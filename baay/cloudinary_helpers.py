"""Helpers Cloudinary destruction (récepteurs post_delete)."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def public_id_and_type(media: Any) -> tuple[str | None, str]:
    """Expose public_id pour API destroy (valeur persistée Django / CloudinaryField)."""
    if not media:
        return None, "image"
    if hasattr(media, "public_id"):
        pid = getattr(media, "public_id", None)
        if pid:
            rtype = getattr(media, "resource_type", None) or "image"
            return str(pid), str(rtype)
    raw = getattr(media, "name", None) if hasattr(media, "name") else None
    if raw is None:
        raw = str(media)
    raw = (raw or "").strip()
    if not raw:
        return None, "image"
    lowered = raw.lower()
    rt = "raw" if "/raw/upload/" in lowered or "resource_type/raw" in lowered else "image"
    if raw.startswith(("http://", "https://")):
        pid = raw.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        return pid, rt
    return raw, rt


def destroy_cloudinary_value(media: Any) -> None:
    if not media:
        return
    pid, resource_type = public_id_and_type(media)
    if not pid:
        return
    try:
        import cloudinary.uploader
    except ImportError:
        logger.warning("cloudinary absent : purge ignorée (%s)", pid)
        return
    try:
        cloudinary.uploader.destroy(pid, invalidate=True, resource_type=resource_type)
    except Exception as exc:
        logger.warning(
            "destroy Cloudinary ignoré ou échoué (public_id=%s) : %s",
            pid,
            exc,
        )
