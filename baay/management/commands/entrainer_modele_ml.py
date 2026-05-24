"""
Commande Django : entrainer_modele_ml
======================================
Entraine un modele XGBoost de prediction de rendement par culture a partir
du dataset collecte dans PrevisionFeatures (projets clotures uniquement).

Prerequis
---------
    pip install numpy>=2.0 scikit-learn>=1.5 xgboost>=2.0

Usage
-----
    python manage.py entrainer_modele_ml --culture Mil --min-n 50
    python manage.py entrainer_modele_ml --culture Arachide --min-n 20 --cv 5
    python manage.py entrainer_modele_ml --all --min-n 30
    python manage.py entrainer_modele_ml --list

Options
-------
--culture   Nom de la culture (partiel, insensible casse). Peut se répéter.
--all       Entraine un modele pour chaque culture ayant assez de donnees.
--min-n     Seuil minimum d'observations pour entrainer (defaut: 30).
--cv        Nombre de folds de cross-validation (defaut: 5).
--output    Dossier de sortie (defaut: MEDIA_ROOT/ml_models/).
--list      Affiche les cultures disponibles et leur nombre d'observations.

Modele sauvegarde
-----------------
    MEDIA_ROOT/ml_models/<slug_culture>.pkl
Contenu du fichier pkl :
    {model, features, encoders, meta: {culture, n_train, rmse_cv, r2_cv, date}}
"""

import pickle
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Entraine un modele XGBoost de prediction de rendement par culture."

    def add_arguments(self, parser):
        parser.add_argument(
            "--culture",
            action="append",
            dest="cultures",
            default=None,
            help="Nom de culture (repetable). Incompatible avec --all.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            default=False,
            help="Entrainer pour toutes les cultures avec assez de donnees.",
        )
        parser.add_argument(
            "--min-n",
            type=int,
            default=30,
            help="Observations minimum par culture (defaut: 30).",
        )
        parser.add_argument(
            "--cv",
            type=int,
            default=5,
            help="Nombre de folds cross-validation (defaut: 5).",
        )
        parser.add_argument(
            "--output",
            default=None,
            help="Dossier de sortie des fichiers .pkl.",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            default=False,
            help="Lister les cultures disponibles et quitter.",
        )

    def handle(self, *args, **options):
        try:
            import numpy as np
            import pandas as pd
            from sklearn.model_selection import cross_val_score
            from sklearn.preprocessing import LabelEncoder
            from xgboost import XGBRegressor
        except ImportError as e:
            raise CommandError(
                f"Dependances manquantes : {e}\n"
                "Installez : pip install numpy>=2.0 scikit-learn>=1.5 xgboost>=2.0"
            )

        from baay.models import PrevisionFeatures
        from baay.services.ml_service import FEATURE_ORDER, _CATEGORICAL_FEATURES, _slug

        # ── Chargement du dataset ────────────────────────────────────────────
        qs = (
            PrevisionFeatures.objects.filter(rendement_reel__isnull=False)
            .select_related("prevision__projet_produit__produit")
        )

        rows = []
        for feat in qs.iterator(chunk_size=500):
            try:
                nom = feat.prevision.projet_produit.produit.nom
            except Exception:
                continue
            row = {"_culture": nom, "_rendement_reel": feat.rendement_reel}
            row.update(feat.features)
            rows.append(row)

        if not rows:
            self.stderr.write(self.style.WARNING(
                "Aucune donnee validee. Cloturez des projets avec rendement_final."
            ))
            return

        df = pd.DataFrame(rows)

        # ── Mode --list ──────────────────────────────────────────────────────
        if options["list"]:
            self.stdout.write("\nCultures disponibles :")
            for culture, group in df.groupby("_culture"):
                flag = " OK" if len(group) >= options["min_n"] else f" (< {options['min_n']} obs)"
                self.stdout.write(f"  {culture:<25} {len(group):>4} obs{flag}")
            return

        # ── Sélection des cultures à entraîner ───────────────────────────────
        cultures_input = options["cultures"]
        entrainer_tout = options["all"]

        if not cultures_input and not entrainer_tout:
            raise CommandError("Spécifiez --culture NOM ou --all.")

        if entrainer_tout:
            cultures_selectionnees = [
                c for c, g in df.groupby("_culture")
                if len(g) >= options["min_n"]
            ]
        else:
            cultures_selectionnees = []
            for filtre in (cultures_input or []):
                matches = [c for c in df["_culture"].unique()
                           if filtre.lower() in c.lower()]
                if not matches:
                    self.stderr.write(self.style.WARNING(
                        f"Culture '{filtre}' introuvable dans le dataset."
                    ))
                else:
                    cultures_selectionnees.extend(matches)

        if not cultures_selectionnees:
            raise CommandError("Aucune culture trouvee avec assez de donnees.")

        # ── Dossier de sortie ────────────────────────────────────────────────
        output_dir = Path(options["output"] or
                          Path(getattr(settings, "MEDIA_ROOT", "media")) / "ml_models")
        output_dir.mkdir(parents=True, exist_ok=True)

        # ── Entraînement par culture ─────────────────────────────────────────
        resultats = []
        for culture in sorted(set(cultures_selectionnees)):
            df_c = df[df["_culture"] == culture].copy()
            n = len(df_c)

            if n < options["min_n"]:
                self.stderr.write(self.style.WARNING(
                    f"[{culture}] Seulement {n} obs (min requis: {options['min_n']}) — ignore."
                ))
                continue

            self.stdout.write(f"\n[{culture}] Entrainement sur {n} observations...")

            # Preparer X et y
            feature_cols = [f for f in FEATURE_ORDER if f in df_c.columns]
            X_df = df_c[feature_cols].copy()
            y = df_c["_rendement_reel"].astype(float).values

            # Encoder les variables catégorielles
            encoders = {}
            for col in _CATEGORICAL_FEATURES:
                if col in X_df.columns:
                    le = LabelEncoder()
                    X_df[col] = X_df[col].fillna("Inconnu").astype(str)
                    X_df[col] = le.fit_transform(X_df[col])
                    encoders[col] = le

            # Convertir les booléens
            for col in ["sol_inadapte", "deficit_hydrique"]:
                if col in X_df.columns:
                    X_df[col] = X_df[col].fillna(False).astype(int)

            # Remplir les NaN numériques par 0
            X_df = X_df.fillna(0)
            X = X_df.values.astype(float)

            # Modele XGBoost
            model = XGBRegressor(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbosity=0,
            )

            # Cross-validation
            n_folds = min(options["cv"], n)
            try:
                scores_r2 = cross_val_score(model, X, y, cv=n_folds, scoring="r2")
                scores_neg_rmse = cross_val_score(
                    model, X, y, cv=n_folds, scoring="neg_root_mean_squared_error"
                )
                r2_cv = float(scores_r2.mean())
                rmse_cv = float(-scores_neg_rmse.mean())
            except Exception as exc:
                self.stderr.write(self.style.WARNING(f"  CV echouee : {exc}"))
                r2_cv = 0.0
                rmse_cv = 0.0

            # Entraînement final sur toutes les données
            model.fit(X, y)

            # Sauvegarde
            pkl_path = output_dir / f"{_slug(culture)}.pkl"
            modele_dict = {
                "model": model,
                "features": feature_cols,
                "encoders": encoders,
                "meta": {
                    "culture": culture,
                    "n_train": n,
                    "rmse_cv": round(rmse_cv, 2),
                    "r2_cv": round(r2_cv, 4),
                    "date_entrainement": datetime.now(timezone.utc).isoformat(),
                },
            }
            with pkl_path.open("wb") as f:
                pickle.dump(modele_dict, f, protocol=pickle.HIGHEST_PROTOCOL)

            resultats.append({
                "culture": culture, "n": n,
                "r2": r2_cv, "rmse": rmse_cv, "pkl": pkl_path,
            })

            self.stdout.write(self.style.SUCCESS(
                f"  R2={r2_cv:.3f}  RMSE={rmse_cv:.0f} kg  -> {pkl_path.name}"
            ))

        # ── Rapport final ────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            f"\n=== Entrainement termine : {len(resultats)} modele(s) ===\n"
            f"  Dossier : {output_dir.resolve()}"
        ))
        for r in resultats:
            qualite = "Excellent" if r["r2"] > 0.7 else "Bon" if r["r2"] > 0.4 else "A ameliorer"
            self.stdout.write(
                f"  {r['culture']:<25} n={r['n']:>4}  R2={r['r2']:.3f}  "
                f"RMSE={r['rmse']:>7.0f} kg  [{qualite}]"
            )
