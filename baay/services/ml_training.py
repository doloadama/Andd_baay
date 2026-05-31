"""
Service d'entraînement ML continu — baay/services/ml_training.py
=================================================================
Expose deux fonctions publiques :

  entrainer_culture(culture_nom, ...)
      Entraîne (ou ré-entraîne en warm-start) un modèle XGBoost pour une
      culture et enregistre le résultat dans MLModeleInfo.

  cultures_a_reentrainer(min_new_obs)
      Liste les cultures ayant accumulé assez de nouvelles observations
      validées depuis leur dernier entraînement.

Ces fonctions sont appelées par :
  - ``entrainer_modele_ml`` (commande management) — usage manuel / CI
  - ``auto_retrain_models_task`` (Celery Beat) — apprentissage continu

Warm-start XGBoost
------------------
Quand ``warm_start=True`` et qu'un modèle .pkl existe déjà, on extrait le
booster sous-jacent et on l'utilise comme point de départ via
``XGBRegressor.fit(X, y, xgb_model=existing_booster)``.
Cela ajoute des arbres sur le modèle précédent au lieu de tout réapprendre,
préservant la mémoire des données historiques.

Stratégie de remplacement
--------------------------
Un nouveau modèle ne remplace l'ancien en production que si son R² CV est
au moins aussi bon (tolérance -0.05). Cela évite de dégrader les prédictions
sur un petit batch de nouvelles données bruitées.
"""

from __future__ import annotations

import logging
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Seuil : nb de nouvelles observations (validées depuis le dernier entraînement)
# avant de déclencher un ré-entraînement automatique.
MIN_NEW_OBS_AUTO: int = 5


def _get_output_dir(override: str | None = None) -> Path:
    base = Path(getattr(settings, "MEDIA_ROOT", "media")) / "ml_models"
    p = Path(override) if override else base
    p.mkdir(parents=True, exist_ok=True)
    return p


def entrainer_culture(
    culture_nom: str,
    *,
    min_n: int = 30,
    n_cv: int = 5,
    warm_start: bool = False,
    declencheur: str = "manuel",
    output_dir: str | None = None,
    forcer_remplacement: bool = False,
) -> dict | None:
    """
    Entraîne ou ré-entraîne un modèle XGBoost pour ``culture_nom``.

    Parameters
    ----------
    culture_nom : str
        Nom exact de la culture (ex. "Mil blanc", "Arachide coque").
    min_n : int
        Nombre minimum d'observations labellisées pour lancer l'entraînement.
    n_cv : int
        Nombre de folds pour la cross-validation.
    warm_start : bool
        Si True, charge le booster existant et ajoute des arbres dessus.
    declencheur : str
        Origine de l'appel : 'manuel', 'auto' ou 'signal'.
    output_dir : str | None
        Dossier de sortie des .pkl (par défaut MEDIA_ROOT/ml_models/).
    forcer_remplacement : bool
        Si True, sauvegarde même si R² est légèrement dégradé.

    Returns
    -------
    dict | None
        {'culture', 'n', 'r2', 'rmse', 'pkl_path', 'improved', 'warm_start_used'}
        None si pas assez de données.
    """
    # Imports optionnels (évite ImportError au chargement du module)
    try:
        import numpy as np  # noqa: F401
        import pandas as pd
        from sklearn.model_selection import GroupKFold, cross_val_score
        from sklearn.preprocessing import LabelEncoder
        from xgboost import XGBRegressor
    except ImportError as exc:
        logger.error("Dependances ML manquantes : %s", exc)
        return None

    from baay.models import MLModeleInfo, PrevisionFeatures
    from baay.services.ml_service import (
        PRECAMPAGNE_FEATURES, MIN_R2, _CATEGORICAL_FEATURES, _slug,
    )

    culture_slug = _slug(culture_nom)

    # ── Chargement du dataset pour cette culture ──────────────────────────────
    qs = (
        PrevisionFeatures.objects.filter(
            rendement_reel__isnull=False,
            prevision__projet_produit__produit__nom__iexact=culture_nom,
        )
        .select_related(
            "prevision__projet_produit__produit",
            "prevision__projet_produit__projet",
        )
    )

    rows = []
    for feat in qs.iterator(chunk_size=500):
        row = {"_rendement_reel": feat.rendement_reel}
        row.update(feat.features or {})
        # Localité = groupe pour la validation croisée (anti-fuite spatiale).
        try:
            row["_localite_id"] = feat.prevision.projet_produit.projet.localite_id
        except Exception:
            row["_localite_id"] = row.get("localite_id")
        rows.append(row)

    n = len(rows)
    if n < min_n:
        logger.info(
            "[%s] Seulement %d obs (min requis: %d) — entraînement ignoré.",
            culture_nom, n, min_n,
        )
        return None

    df = pd.DataFrame(rows)
    # Features ANTI-FUITE uniquement (pas les sorties du moteur à règles).
    feature_cols = [f for f in PRECAMPAGNE_FEATURES if f in df.columns]
    X_df = df[feature_cols].copy()
    y = df["_rendement_reel"].astype(float).values
    groups = df["_localite_id"].values if "_localite_id" in df.columns else None

    # Encoder les variables catégorielles
    encoders = {}
    for col in _CATEGORICAL_FEATURES:
        if col in X_df.columns:
            le = LabelEncoder()
            X_df[col] = X_df[col].fillna("Inconnu").astype(str)
            X_df[col] = le.fit_transform(X_df[col])
            encoders[col] = le

    for col in ("sol_inadapte", "deficit_hydrique"):
        if col in X_df.columns:
            X_df[col] = X_df[col].fillna(False).astype(int)

    X_df = X_df.fillna(0)
    X = X_df.values.astype(float)

    # ── Warm-start : charger le booster existant ──────────────────────────────
    output_dir_path = _get_output_dir(output_dir)
    pkl_path = output_dir_path / f"{culture_slug}.pkl"
    existing_booster = None
    warm_start_used = False

    if warm_start and pkl_path.exists():
        try:
            with pkl_path.open("rb") as f:
                old_dict = pickle.load(f)
            old_model = old_dict.get("model")
            if old_model is not None:
                existing_booster = old_model.get_booster()
                warm_start_used = True
                logger.info("[%s] Warm-start : booster existant chargé.", culture_nom)
        except Exception as exc:
            logger.warning("[%s] Warm-start impossible : %s — entraînement from scratch.", culture_nom, exc)

    # ── Modèle XGBoost ────────────────────────────────────────────────────────
    # Warm-start : moins de rounds (on ajoute des arbres), learning rate plus fin
    n_estimators = 50 if warm_start_used else 200
    learning_rate = 0.03 if warm_start_used else 0.05

    model = XGBRegressor(
        n_estimators=n_estimators,
        max_depth=4,
        learning_rate=learning_rate,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )

    # Cross-validation — split PAR LOCALITÉ si possible (évite la fuite spatiale :
    # une même localité dans train ET test gonflerait artificiellement le R²).
    r2_cv = 0.0
    rmse_cv = 0.0
    cv_kwargs = {}
    n_groupes = len(set(g for g in (groups if groups is not None else []) if g is not None))
    if groups is not None and n_groupes >= 2:
        cv = GroupKFold(n_splits=min(n_cv, n_groupes))
        cv_kwargs["groups"] = groups
    else:
        cv = min(n_cv, n)   # repli : KFold classique
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            scores_r2 = cross_val_score(model, X, y, cv=cv, scoring="r2", **cv_kwargs)
            scores_rmse = cross_val_score(
                model, X, y, cv=cv, scoring="neg_root_mean_squared_error", **cv_kwargs
            )
        r2_cv = float(scores_r2.mean())
        rmse_cv = float(-scores_rmse.mean())
    except Exception as exc:
        logger.warning("[%s] CV échouée : %s", culture_nom, exc)

    # Entraînement final sur toutes les données
    if warm_start_used and existing_booster is not None:
        model.fit(X, y, xgb_model=existing_booster)
    else:
        model.fit(X, y)

    # ── Décision de remplacement ──────────────────────────────────────────────
    prev_r2 = MLModeleInfo.meilleur_r2(culture_slug)
    # Un modèle n'est mis en production que s'il EXPLIQUE réellement (R² ≥ MIN_R2)
    # ET n'est pas plus mauvais que le précédent (tolérance -0.05).
    explicatif = r2_cv >= MIN_R2
    improved = forcer_remplacement or (
        explicatif and (prev_r2 is None or r2_cv >= (prev_r2 - 0.05))
    )
    if not explicatif and not forcer_remplacement:
        logger.info(
            "[%s] R²=%.3f < seuil %.2f — modèle NON activé (non explicatif).",
            culture_nom, r2_cv, MIN_R2,
        )

    # ── Sauvegarde .pkl ───────────────────────────────────────────────────────
    if improved:
        modele_dict = {
            "model": model,
            "features": feature_cols,
            "encoders": encoders,
            "meta": {
                "culture": culture_nom,
                "n_train": n,
                "rmse_cv": round(rmse_cv, 2),
                "r2_cv": round(r2_cv, 4),
                "date_entrainement": datetime.now(timezone.utc).isoformat(),
                "declencheur": declencheur,
                "warm_start": warm_start_used,
            },
        }
        with pkl_path.open("wb") as f:
            pickle.dump(modele_dict, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info(
            "[%s] Modèle sauvegardé — R²=%.3f RMSE=%.0f kg warm_start=%s.",
            culture_nom, r2_cv, rmse_cv, warm_start_used,
        )
    else:
        logger.info(
            "[%s] Nouveau modèle (R²=%.3f) moins bon que précédent (R²=%.3f) — non remplacé.",
            culture_nom, r2_cv, prev_r2,
        )

    # ── Enregistrement dans MLModeleInfo ──────────────────────────────────────
    # Désactiver les anciennes entrées actives pour cette culture
    if improved:
        MLModeleInfo.objects.filter(culture_slug=culture_slug, actif=True).update(actif=False)

    MLModeleInfo.objects.create(
        culture_slug=culture_slug,
        culture_nom=culture_nom,
        n_observations=n,
        r2_score=round(r2_cv, 4) if r2_cv is not None else None,
        rmse=round(rmse_cv, 2) if rmse_cv is not None else None,
        actif=improved,
        declencheur=declencheur,
        warm_start=warm_start_used,
        fichier_pkl=str(pkl_path),
    )

    return {
        "culture": culture_nom,
        "n": n,
        "r2": r2_cv,
        "rmse": rmse_cv,
        "pkl_path": pkl_path,
        "improved": improved,
        "warm_start_used": warm_start_used,
    }


def cultures_a_reentrainer(min_new_obs: int = MIN_NEW_OBS_AUTO) -> list[str]:
    """
    Retourne les cultures ayant ≥ ``min_new_obs`` nouvelles observations
    labellisées depuis leur dernier entraînement.

    Une culture "sans historique d'entraînement" est incluse si elle a
    au moins ``min_new_obs`` observations au total.
    """
    from baay.models import MLModeleInfo, PrevisionFeatures
    from baay.services.ml_service import _slug

    cultures = list(
        PrevisionFeatures.objects.filter(rendement_reel__isnull=False)
        .values_list("prevision__projet_produit__produit__nom", flat=True)
        .distinct()
    )

    a_reentrainer: list[str] = []
    for culture_nom in cultures:
        if not culture_nom:
            continue
        slug = _slug(culture_nom)
        last_date = MLModeleInfo.derniere_date_entrainement(slug)

        qs = PrevisionFeatures.objects.filter(
            rendement_reel__isnull=False,
            prevision__projet_produit__produit__nom__iexact=culture_nom,
        )
        if last_date is not None:
            qs = qs.filter(date_validation__gte=last_date)

        if qs.count() >= min_new_obs:
            a_reentrainer.append(culture_nom)

    return a_reentrainer
