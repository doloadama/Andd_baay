"""Chemins dossiers médias Cloudinary (préfixe environnement × type entité)."""
from django.conf import settings


def cloudinary_media_folder(subpath: str) -> str:
    """
    Construit le dossier Cloudinary racine sous forme `{prefix}/{subpath}`.
    `CLOUDINARY_MEDIA_PREFIX` (settings) vaut typiquement `dev` ou `prod`.
    """
    base = (getattr(settings, "CLOUDINARY_MEDIA_PREFIX", None) or "dev").strip().strip("/")
    subpath = (subpath or "").strip().strip("/")
    return f"{base}/{subpath}" if subpath else base
