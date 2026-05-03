import json
import os
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings

from baay.models import Pays, Localite


class Command(BaseCommand):
    help = (
        "Peuple la base avec les pays africains et leurs regions administratives de premier niveau "
        "a partir d'un fichier JSON. Par defaut, utilise baay/data/seed_geo.json."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            dest="file",
            default=None,
            help="Chemin vers le fichier JSON (defaut: baay/data/seed_geo.json)",
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Affiche les operations sans ecrire en base",
        )

    def handle(self, *args, **options):
        file_path = options.get("file")
        if not file_path:
            file_path = os.path.join(settings.BASE_DIR, "baay", "data", "seed_geo.json")
        file_path = os.path.abspath(file_path)

        if not os.path.exists(file_path):
            raise CommandError(f"Fichier introuvable: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            try:
                payload = json.load(f)
            except Exception as e:
                raise CommandError(f"JSON invalide: {e}")

        countries: list[dict[str, Any]] = payload.get("countries") or []
        if not countries:
            self.stdout.write(self.style.WARNING("Aucun pays a inserer (cle 'countries' vide)."))
            return

        dry = bool(options.get("dry_run"))

        created_pays = 0
        updated_pays = 0
        created_loc = 0
        skipped_loc = 0

        @transaction.atomic
        def _apply():
            nonlocal created_pays, updated_pays, created_loc, skipped_loc
            for c in countries:
                name = (c.get("name") or "").strip()
                iso = (c.get("iso") or "").strip() or None
                if not name:
                    continue
                pays, created = Pays.objects.get_or_create(nom=name, defaults={"code_iso": iso})
                if not created and iso and pays.code_iso != iso:
                    pays.code_iso = iso
                    pays.save(update_fields=["code_iso"])
                    updated_pays += 1
                elif created:
                    created_pays += 1

                regions = c.get("regions") or []
                for r in regions:
                    rname = (r or "").strip()
                    if not rname:
                        continue
                    # Localite.nom est unique: pour eviter les collisions inter-pays, suffixons par l'ISO (si dispo)
                    unique_name = f"{rname} — {iso}" if iso else f"{rname} — {name}"
                    loc, loc_created = Localite.objects.get_or_create(
                        nom=unique_name,
                        defaults={
                            "pays": pays,
                        },
                    )
                    if loc_created:
                        created_loc += 1
                    else:
                        # Aligne le lien pays si absent
                        if not loc.pays_id:
                            loc.pays = pays
                            loc.save(update_fields=["pays"])
                        else:
                            skipped_loc += 1

        if dry:
            self.stdout.write(self.style.WARNING("Mode simulation (dry-run): aucune ecriture."))
            # Simuler sans commit: on laisse la transaction outer rollback implicite en fin
            with transaction.atomic():
                _apply()
                transaction.set_rollback(True)
        else:
            _apply()

        self.stdout.write(
            self.style.SUCCESS(
                f"OK: Pays crees={created_pays}, pays_maj={updated_pays}, localites_creees={created_loc}, localites_ignorees={skipped_loc}."
            )
        )
