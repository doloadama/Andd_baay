import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from baay.cloudinary_helpers import public_id_and_type
from baay.cloudinary_paths import cloudinary_media_folder
from baay.models import (
    Depense,
    Ferme,
    Investissement,
    MembreFerme,
    Message,
    PhotoProduitAgricole,
    Projet,
    ProjetProduit,
    Recette,
)


def _looks_like_local_path(value: str) -> bool:
    if not value:
        return False
    lowered = value.lower()
    if lowered.startswith(("http://", "https://")):
        return False
    return True


def _resolve_local_file(value: str) -> Path | None:
    """
    Convert a DB value (legacy ImageField path) into an absolute file path under MEDIA_ROOT.
    Supports values with/without MEDIA_URL prefix.
    """
    if not value:
        return None
    raw = value.strip().lstrip("/").replace("\\", "/")
    media_url = (getattr(settings, "MEDIA_URL", "") or "").strip()
    if media_url:
        media_url_norm = media_url.strip().lstrip("/").replace("\\", "/")
        if raw.startswith(media_url_norm):
            raw = raw[len(media_url_norm) :].lstrip("/")

    media_root = Path(getattr(settings, "MEDIA_ROOT", "") or "")
    if not str(media_root):
        return None
    candidate = (media_root / raw).resolve()
    try:
        candidate.relative_to(media_root.resolve())
    except Exception:
        return None
    return candidate


def _upload_to_cloudinary(local_path: Path, *, folder: str, resource_type: str) -> str:
    import cloudinary.uploader

    res = cloudinary.uploader.upload(
        str(local_path),
        folder=folder,
        resource_type=resource_type,
        overwrite=False,
        invalidate=True,
        unique_filename=True,
    )
    public_id = (res or {}).get("public_id")
    if not public_id:
        raise RuntimeError("Cloudinary upload returned no public_id")
    return str(public_id)


class Command(BaseCommand):
    help = "Migrate legacy local MEDIA files to Cloudinary and update CloudinaryField values."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Do not upload or save, only print actions.")
        parser.add_argument("--limit", type=int, default=0, help="Max number of files to process (0 = no limit).")
        parser.add_argument(
            "--delete-local",
            action="store_true",
            help="Delete the local file after a successful upload + DB update.",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "CLOUDINARY_ACTIVE", False):
            self.stderr.write(self.style.ERROR("CLOUDINARY_URL absent: Cloudinary is not active. Aborting."))
            return

        dry_run: bool = bool(options["dry_run"])
        limit: int = int(options["limit"] or 0)
        delete_local: bool = bool(options["delete_local"])

        # (model, field_name, folder_subpath, resource_type)
        targets = [
            (Ferme, "image_couverture", "fermes", "image"),
            (Ferme, "image_infrastructure", "fermes/infrastructures", "image"),
            (MembreFerme, "photo_profil", "profils", "image"),
            (Projet, "image_fond", "projets/couvertures", "image"),
            (ProjetProduit, "image", "projets/plants", "image"),
            (PhotoProduitAgricole, "image", "catalogue/photos", "image"),
            (Recette, "justificatif_facture", "finance/recettes", "auto"),
            (Depense, "justificatif", "finance/depenses", "auto"),
            (Investissement, "piece_justificative", "finance/investissements", "auto"),
            (Message, "piece_jointe", "messagerie/pieces_jointes", "auto"),
        ]

        processed = 0
        migrated = 0
        skipped = 0
        missing = 0
        failed = 0

        for model, field_name, folder_subpath, resource_type in targets:
            qs = model.objects.exclude(**{f"{field_name}__isnull": True}).exclude(**{field_name: ""})
            self.stdout.write(f"\n== {model.__name__}.{field_name} ({qs.count()} candidate rows) ==")

            for obj in qs.iterator(chunk_size=200):
                if limit and processed >= limit:
                    self.stdout.write(self.style.WARNING(f"Limit reached ({limit}). Stopping."))
                    self.stdout.write(
                        f"Summary: processed={processed}, migrated={migrated}, skipped={skipped}, missing={missing}, failed={failed}"
                    )
                    return

                processed += 1

                value = getattr(obj, field_name)
                raw = getattr(value, "name", None) or str(value or "")
                raw = raw.strip()

                # Already a Cloudinary asset? (public_id is usually not a local path)
                pid, _rt = public_id_and_type(value)
                if pid and not _looks_like_local_path(pid):
                    skipped += 1
                    continue

                if not _looks_like_local_path(raw):
                    skipped += 1
                    continue

                local_path = _resolve_local_file(raw)
                if not local_path or not local_path.exists():
                    missing += 1
                    self.stdout.write(self.style.WARNING(f"- Missing: {model.__name__}({obj.pk}) {field_name}={raw}"))
                    continue

                folder = cloudinary_media_folder(folder_subpath)
                self.stdout.write(f"- Upload: {model.__name__}({obj.pk}) {field_name} <- {local_path}")
                if dry_run:
                    continue

                try:
                    with transaction.atomic():
                        public_id = _upload_to_cloudinary(
                            local_path,
                            folder=folder,
                            resource_type=resource_type,
                        )
                        setattr(obj, field_name, public_id)
                        obj.save(update_fields=[field_name])
                    migrated += 1
                    if delete_local:
                        try:
                            os.remove(local_path)
                        except OSError:
                            pass
                except Exception as exc:
                    failed += 1
                    self.stderr.write(
                        self.style.ERROR(
                            f"! Failed: {model.__name__}({obj.pk}) {field_name} file={local_path} err={exc}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. processed={processed}, migrated={migrated}, skipped={skipped}, missing={missing}, failed={failed}"
            )
        )
