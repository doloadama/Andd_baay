"""
Commande Django : exporter_dataset_ml
======================================
Exporte le dataset d'entrainement ML issu de PrevisionFeatures.

Seuls les enregistrements valides (rendement_reel non nul) sont inclus,
ce qui correspond aux projets clotures avec un rendement_final saisi.

Usage
-----
    python manage.py exporter_dataset_ml
    python manage.py exporter_dataset_ml --format json
    python manage.py exporter_dataset_ml --culture Mil --min-n 10
    python manage.py exporter_dataset_ml --output /tmp/dataset.csv

Options
-------
--format    csv (defaut) | json
--culture   Filtrer par nom de culture (recherche partielle insensible a la casse)
--min-n     Nombre minimum d'observations pour inclure une culture (defaut: 1)
--output    Chemin du fichier de sortie (defaut: dataset_ml_<timestamp>.csv/json)
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q


class Command(BaseCommand):
    help = "Exporte le dataset ML (PrevisionFeatures valides) en CSV ou JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            choices=["csv", "json"],
            default="csv",
            help="Format de sortie : csv (defaut) ou json.",
        )
        parser.add_argument(
            "--culture",
            default=None,
            help="Filtrer par nom de culture (partiel, insensible casse).",
        )
        parser.add_argument(
            "--min-n",
            type=int,
            default=1,
            help="Nombre minimum d'observations par culture (defaut: 1).",
        )
        parser.add_argument(
            "--output",
            default=None,
            help="Chemin de sortie. Defaut : dataset_ml_<timestamp>.<ext>.",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            default=False,
            help="Affiche les cultures disponibles et leur nombre d'observations, puis quitte.",
        )

    def handle(self, *args, **options):
        from baay.models import PrevisionFeatures

        fmt = options["format"]
        culture_filtre = options["culture"]
        min_n = options["min_n"]
        output_path = options["output"]

        if options["list"]:
            qs_all = (
                PrevisionFeatures.objects.filter(rendement_reel__isnull=False)
                .select_related("prevision__projet_produit__produit")
            )
            compteur = {}
            for feat in qs_all.iterator(chunk_size=500):
                try:
                    nom = feat.prevision.projet_produit.produit.nom
                except Exception:
                    nom = "Inconnu"
                compteur[nom] = compteur.get(nom, 0) + 1
            if not compteur:
                self.stdout.write(self.style.WARNING(
                    "Aucune observation validee. Cloturez des projets avec rendement_final."
                ))
                return
            self.stdout.write("\nCultures disponibles dans le dataset ML :")
            for culture, n in sorted(compteur.items(), key=lambda x: -x[1]):
                flag = " OK" if n >= min_n else f" (< {min_n} obs)"
                self.stdout.write(f"  {culture:<25} {n:>4} obs{flag}")
            self.stdout.write(f"\n  Total : {sum(compteur.values())} observations, {len(compteur)} culture(s).")
            return

        qs = (
            PrevisionFeatures.objects.filter(rendement_reel__isnull=False)
            .select_related(
                "prevision__projet_produit__produit",
                "prevision__projet_produit__projet__localite",
            )
            .order_by("date_creation")
        )

        if culture_filtre:
            qs = qs.filter(
                prevision__projet_produit__produit__nom__icontains=culture_filtre
            )

        rows = []
        compteur_par_culture = {}

        for feat in qs.iterator(chunk_size=500):
            try:
                pp = feat.prevision.projet_produit
                nom_culture = pp.produit.nom if pp and pp.produit else "Inconnu"
            except Exception:
                nom_culture = "Inconnu"

            row = {
                "nom_culture": nom_culture,
                "rendement_reel_kg": feat.rendement_reel,
                "erreur_pct": feat.erreur_pct,
                "date_creation": feat.date_creation.isoformat() if feat.date_creation else None,
                "date_validation": feat.date_validation.isoformat() if feat.date_validation else None,
                **feat.features,   # déplie tout le vecteur JSON en colonnes
            }
            rows.append(row)
            compteur_par_culture[nom_culture] = compteur_par_culture.get(nom_culture, 0) + 1

        # Appliquer le filtre min-n
        if min_n > 1:
            cultures_ok = {c for c, n in compteur_par_culture.items() if n >= min_n}
            rows = [r for r in rows if r["nom_culture"] in cultures_ok]

        if not rows:
            self.stderr.write(self.style.WARNING(
                "Aucune observation validee trouvee. "
                "Renseignez ProjetProduit.rendement_final lors de la cloture des projets."
            ))
            return

        # Chemin de sortie
        if not output_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"dataset_ml_{ts}.{fmt}"

        output_path = Path(output_path)

        if fmt == "csv":
            self._write_csv(rows, output_path)
        else:
            self._write_json(rows, output_path)

        # Rapport
        self.stdout.write(self.style.SUCCESS(
            f"\n=== Dataset ML exporte ===\n"
            f"  Observations totales : {len(rows)}\n"
            f"  Cultures              : {len(compteur_par_culture)}\n"
            f"  Fichier               : {output_path.resolve()}\n"
        ))

        # Detail par culture
        self.stdout.write("  Detail par culture :")
        for culture, n in sorted(compteur_par_culture.items()):
            flag = "" if n >= min_n else " [exclu, n<min-n]"
            self.stdout.write(f"    {culture:<25} {n:>4} obs{flag}")

    def _write_csv(self, rows: list[dict], path: Path) -> None:
        if not rows:
            return
        # Toutes les cles comme en-tetes (union de toutes les lignes)
        fieldnames = list(rows[0].keys())
        for row in rows[1:]:
            for k in row:
                if k not in fieldnames:
                    fieldnames.append(k)

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    def _write_json(self, rows: list[dict], path: Path) -> None:
        with path.open("w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
