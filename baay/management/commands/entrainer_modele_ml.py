"""
Commande Django : entrainer_modele_ml
======================================
Entraine ou ré-entraîne un modèle XGBoost de prédiction de rendement par
culture à partir du dataset collecté dans PrevisionFeatures.

Utilise ``baay.services.ml_training.entrainer_culture()`` — la même fonction
que la tâche Celery ``auto_retrain_models_task`` — pour garantir un
comportement identique quelle que soit l'origine de l'entraînement.

Prérequis
---------
    pip install numpy>=2.0 scikit-learn>=1.5 xgboost>=2.0

Usage
-----
    python manage.py entrainer_modele_ml --culture Mil --min-n 5
    python manage.py entrainer_modele_ml --culture Arachide --warm-start
    python manage.py entrainer_modele_ml --all --min-n 5
    python manage.py entrainer_modele_ml --all --warm-start
    python manage.py entrainer_modele_ml --list

Options
-------
--culture     Nom de culture (répétable). Incompatible avec --all.
--all         Entraîne pour toutes les cultures ayant assez de données.
--min-n       Seuil minimum d'observations (défaut: 5).
--cv          Folds de cross-validation (défaut: 5).
--warm-start  Ajoute des arbres sur le modèle existant (ne réapprend pas de zéro).
--output      Dossier de sortie des .pkl (défaut: MEDIA_ROOT/ml_models/).
--list        Liste les cultures disponibles et quitte.

Modèles sauvegardés
-------------------
    MEDIA_ROOT/ml_models/<slug_culture>.pkl
    Contenu : {model, features, encoders, meta: {culture, n_train, rmse_cv, r2_cv, date, warm_start}}

Historique
----------
    Chaque entraînement est tracé dans MLModeleInfo (base de données).
    Voir : python manage.py shell -c "from baay.models import MLModeleInfo; print(MLModeleInfo.objects.all())"
"""

import os
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Entraine (ou ré-entraîne) un modèle XGBoost de prédiction de rendement par culture."

    def add_arguments(self, parser):
        parser.add_argument(
            "--culture",
            action="append",
            dest="cultures",
            default=None,
            metavar="NOM",
            help="Nom de culture (répétable). Incompatible avec --all.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            default=False,
            help="Entraîner pour toutes les cultures avec assez de données.",
        )
        parser.add_argument(
            "--min-n",
            type=int,
            default=5,
            help="Observations minimum par culture (défaut: 5).",
        )
        parser.add_argument(
            "--cv",
            type=int,
            default=5,
            help="Nombre de folds cross-validation (défaut: 5).",
        )
        parser.add_argument(
            "--warm-start",
            action="store_true",
            default=False,
            dest="warm_start",
            help="Ajouter des arbres sur le modèle existant (warm-start XGBoost).",
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
        # Vérifier les dépendances ML
        try:
            import numpy  # noqa: F401
            import pandas  # noqa: F401
            from sklearn.model_selection import cross_val_score  # noqa: F401
            from xgboost import XGBRegressor  # noqa: F401
        except ImportError as e:
            raise CommandError(
                f"Dépendances manquantes : {e}\n"
                "Installez : pip install numpy>=2.0 scikit-learn>=1.5 xgboost>=2.0"
            )

        from baay.models import PrevisionFeatures
        from baay.services.ml_service import _slug
        from baay.services.ml_training import entrainer_culture

        # ── Chargement de la liste des cultures disponibles ──────────────────
        qs = (
            PrevisionFeatures.objects.filter(rendement_reel__isnull=False)
            .select_related("prevision__projet_produit__produit")
        )

        culture_counts: dict[str, int] = {}
        for feat in qs.iterator(chunk_size=500):
            try:
                nom = feat.prevision.projet_produit.produit.nom
            except Exception:
                continue
            culture_counts[nom] = culture_counts.get(nom, 0) + 1

        if not culture_counts:
            self.stderr.write(self.style.WARNING(
                "Aucune donnée validée. Clôturez des projets avec rendement_final."
            ))
            return

        # ── Mode --list ──────────────────────────────────────────────────────
        if options["list"]:
            self.stdout.write("\nCultures disponibles :")
            for culture, count in sorted(culture_counts.items()):
                flag = " [OK]" if count >= options["min_n"] else f" (< {options['min_n']} obs)"
                self.stdout.write(f"  {culture:<28} {count:>4} obs{flag}")

            # Afficher l'historique MLModeleInfo
            from baay.models import MLModeleInfo
            if MLModeleInfo.objects.exists():
                self.stdout.write("\nHistorique des entraînements (5 derniers) :")
                for info in MLModeleInfo.objects.order_by('-date_entrainement')[:5]:
                    ws = " [ws]" if info.warm_start else ""
                    actif = " [ACTIF]" if info.actif else ""
                    r2_s = f"R²={info.r2_score:.3f}" if info.r2_score is not None else "R²=N/D"
                    self.stdout.write(
                        f"  {info.culture_nom:<22} {info.date_entrainement:%Y-%m-%d %H:%M}"
                        f"  {r2_s}  n={info.n_observations}"
                        f"  [{info.declencheur}]{ws}{actif}"
                    )
            return

        # ── Sélection des cultures à entraîner ───────────────────────────────
        cultures_input = options["cultures"]
        entrainer_tout = options["all"]

        if not cultures_input and not entrainer_tout:
            raise CommandError("Spécifiez --culture NOM ou --all.")

        if entrainer_tout:
            cultures_selectionnees = [
                c for c, count in culture_counts.items()
                if count >= options["min_n"]
            ]
        else:
            cultures_selectionnees = []
            for filtre in (cultures_input or []):
                matches = [c for c in culture_counts if filtre.lower() in c.lower()]
                if not matches:
                    self.stderr.write(self.style.WARNING(
                        f"Culture '{filtre}' introuvable dans le dataset."
                    ))
                else:
                    cultures_selectionnees.extend(matches)

        if not cultures_selectionnees:
            raise CommandError(
                f"Aucune culture trouvée avec >= {options['min_n']} observations."
            )

        warm_start = options["warm_start"]
        output_dir = options["output"]

        # ── Entraînement par culture ──────────────────────────────────────────
        resultats = []
        for culture in sorted(set(cultures_selectionnees)):
            n_dispo = culture_counts.get(culture, 0)
            if n_dispo < options["min_n"]:
                self.stderr.write(self.style.WARNING(
                    f"[{culture}] {n_dispo} obs < {options['min_n']} — ignoré."
                ))
                continue

            ws_label = " (warm-start)" if warm_start else ""
            self.stdout.write(f"\n[{culture}] Entraînement{ws_label} sur {n_dispo} observations...")

            result = entrainer_culture(
                culture,
                min_n=options["min_n"],
                n_cv=options["cv"],
                warm_start=warm_start,
                declencheur="manuel",
                output_dir=output_dir,
            )

            if result is None:
                self.stderr.write(self.style.WARNING(
                    f"[{culture}] Entraînement ignoré (pas assez de données)."
                ))
                continue

            resultats.append(result)

            improved_label = "" if result["improved"] else " (non remplacé — moins bon)"
            ws_used = " [ws]" if result["warm_start_used"] else ""
            self.stdout.write(self.style.SUCCESS(
                f"  R²={result['r2']:.3f}  RMSE={result['rmse']:.0f} kg"
                f"{ws_used}{improved_label}"
            ))

        # ── Rapport final ─────────────────────────────────────────────────────
        if not resultats:
            self.stderr.write(self.style.WARNING("Aucun modèle entraîné."))
            return

        from django.conf import settings as django_settings
        from pathlib import Path
        out_dir = Path(output_dir or
                       Path(getattr(django_settings, "MEDIA_ROOT", "media")) / "ml_models")

        self.stdout.write(self.style.SUCCESS(
            f"\n=== Entraînement terminé : {len(resultats)} modèle(s) ==="
        ))
        self.stdout.write(f"  Dossier : {out_dir.resolve()}")
        for r in resultats:
            qualite = "Excellent" if r["r2"] > 0.7 else "Bon" if r["r2"] > 0.4 else "A ameliorer"
            ws_flag = "[ws] " if r["warm_start_used"] else "     "
            self.stdout.write(
                f"  {r['culture']:<25} n={r['n']:>4}  R²={r['r2']:.3f}"
                f"  RMSE={r['rmse']:>7.0f} kg  {ws_flag}[{qualite}]"
            )

        self.stdout.write(
            "\nProchaines étapes :\n"
            "  python manage.py evaluer_previsions\n"
            "  python manage.py entrainer_modele_ml --list"
        )
