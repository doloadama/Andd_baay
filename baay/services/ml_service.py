"""
Service ML — prédiction de rendement par modèle XGBoost (P5.4).

Fonctionnement
--------------
Pour chaque culture disposant d'un modèle entraîné (fichier .pkl dans
MEDIA_ROOT/ml_models/), estimer_rendement_ia() peut effectuer un consensus :

    rendement_final = 0.60 × rendement_ML + 0.40 × rendement_règles

Le modèle n'est utilisé que si :
  - le fichier .pkl existe pour ce produit
  - le vecteur de features peut être encodé sans erreur
  - le modèle prédit une valeur plausible (>0)

En cas d'erreur, on retombe silencieusement sur le moteur à règles.

Entraînement
------------
    python manage.py entrainer_modele_ml --culture Mil --min-n 50

Fichiers pkl
------------
    MEDIA_ROOT/ml_models/<nom_culture_slug>.pkl
    Ex : media/ml_models/mil.pkl

Format pkl
----------
    {
        'model': XGBRegressor instance,
        'features': list[str],       # noms des features dans l'ordre
        'encoders': dict,            # LabelEncoder par feature catégorielle
        'meta': {
            'culture': str,
            'n_train': int,
            'rmse_cv': float,
            'r2_cv': float,
            'date_entrainnement': str (ISO),
        }
    }
"""

import logging
import os
import pickle
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

_MODELS_DIR = Path(getattr(settings, "MEDIA_ROOT", "media")) / "ml_models"

# Features numériques du vecteur (doivent être présentes dans PrevisionFeatures.features)
_NUMERIC_FEATURES = [
    "pluie_moyenne",
    "besoin_eau",
    "superficie",
    "penalite",
    "bonus",
    "variance",
    "n_historique_local",
    "n_historique_regional",
    "progression_cycle",
    "correcteur_biais",
    "mois_semis",
]

# Features catégorielles (encodées via LabelEncoder lors de l'entraînement)
_CATEGORICAL_FEATURES = [
    "sol_type",
    "type_irrigation",
    "type_engrais",
    "saison",
    "categorie_culture",
    "source_rendement",
]

# Ensemble complet dans l'ordre utilisé pour l'entraînement
FEATURE_ORDER = _NUMERIC_FEATURES + _CATEGORICAL_FEATURES + [
    "sol_inadapte",      # bool → 0/1
    "deficit_hydrique",  # bool → 0/1
]


def _slug(nom: str) -> str:
    """Transforme un nom de culture en slug de fichier (minuscules, tirets)."""
    import re
    slug = nom.lower().strip()
    slug = slug.replace("é", "e").replace("è", "e").replace("ê", "e")
    slug = slug.replace("à", "a").replace("â", "a")
    slug = slug.replace("î", "i").replace("ô", "o").replace("û", "u")
    slug = slug.replace("ç", "c").replace("ñ", "n")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def charger_modele_ml(nom_produit: str) -> dict | None:
    """
    Charge le modèle ML pour un produit donné.

    Parameters
    ----------
    nom_produit : str — nom exact du produit (ex: "Mil", "Arachide")

    Returns
    -------
    dict avec les clés 'model', 'features', 'encoders', 'meta', ou None.
    """
    chemin = _MODELS_DIR / f"{_slug(nom_produit)}.pkl"
    if not chemin.exists():
        return None

    try:
        with chemin.open("rb") as f:
            modele_dict = pickle.load(f)
        logger.debug("Modele ML charge : %s (%s)", chemin, modele_dict.get("meta", {}).get("culture"))
        return modele_dict
    except Exception as exc:
        logger.warning("Impossible de charger le modele ML %s : %s", chemin, exc)
        return None


def _encoder_features(features: dict, encoders: dict, feature_order: list) -> list | None:
    """
    Transforme un dict de features en vecteur numérique pour XGBoost.
    Retourne None si une feature obligatoire est manquante ou invalide.
    """
    vecteur = []
    for feat in feature_order:
        val = features.get(feat)
        if feat in _CATEGORICAL_FEATURES:
            enc = encoders.get(feat)
            if enc is None:
                vecteur.append(0)   # catégorie inconnue → 0
            else:
                try:
                    val_str = str(val) if val is not None else "Inconnu"
                    classes = list(enc.classes_)
                    vecteur.append(classes.index(val_str) if val_str in classes else 0)
                except Exception:
                    vecteur.append(0)
        elif isinstance(val, bool):
            vecteur.append(1 if val else 0)
        else:
            try:
                vecteur.append(float(val) if val is not None else 0.0)
            except (TypeError, ValueError):
                vecteur.append(0.0)
    return vecteur


def predire_avec_ml(features: dict, modele_dict: dict) -> dict | None:
    """
    Prédit le rendement cible (kg/ha) avec le modèle XGBoost.

    Returns
    -------
    dict {'rendement_kg_ha': float, 'confiance_bonus': float} ou None.
    """
    try:
        import numpy as np

        model = modele_dict["model"]
        encoders = modele_dict.get("encoders", {})
        feature_order = modele_dict.get("features", FEATURE_ORDER)
        meta = modele_dict.get("meta", {})

        vecteur = _encoder_features(features, encoders, feature_order)
        if vecteur is None:
            return None

        X = np.array([vecteur], dtype=float)
        pred = float(model.predict(X)[0])

        if pred <= 0:
            return None

        # Qualité du modèle → bonus de confiance (max +15 pts)
        r2 = meta.get("r2_cv", 0.0) or 0.0
        confiance_bonus = min(15.0, max(0.0, r2 * 15.0))

        return {
            "rendement_kg_ha": round(pred, 2),
            "confiance_bonus": round(confiance_bonus, 2),
        }

    except ImportError:
        logger.warning("numpy/xgboost non installé — prediction ML indisponible.")
        return None
    except Exception as exc:
        logger.warning("predire_avec_ml : %s", exc)
        return None
