import hashlib
import logging
from typing import Tuple

import requests

from .gemini_vision import PlantVisionGeminiError, call_gemini_vision
from .image_crops import crop_and_upload

logger = logging.getLogger(__name__)

SUPPORTED_MIME = {"image/jpeg", "image/jpg", "image/png"}
CROP_MIME = {"image/jpeg", "image/jpg", "image/png"}


class PlantVisionError(Exception):
    """Erreur métier pour l'analyse de culture."""


def fetch_image_from_url(url: str, timeout: int = 45) -> Tuple[bytes, str]:
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise PlantVisionError("Impossible de télécharger la photo.") from exc
    content_type = (resp.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip().lower()
    if content_type not in SUPPORTED_MIME:
        raise PlantVisionError(f"Format non supporté ({content_type}). Utilisez JPEG ou PNG.")
    return resp.content, content_type


def image_content_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def analyze_plant_pest(
    image_bytes: bytes,
    content_type: str,
    *,
    crop_name: str = "",
    upload_crops: bool = True,
    language: str = "fr",
) -> dict:
    """
    Pipeline complet : Gemini → validation minimale → recadrages Cloudinary.
    """
    if content_type not in SUPPORTED_MIME:
        raise PlantVisionError("Format d'image non supporté.")

    try:
        data = call_gemini_vision(image_bytes, content_type, crop_name=crop_name, language=language)
    except PlantVisionGeminiError as exc:
        raise PlantVisionError(str(exc)) from exc

    detections = data.get("detections") or []
    if upload_crops and detections and content_type in CROP_MIME:
        try:
            data["detections"] = crop_and_upload(image_bytes, detections)
        except Exception as exc:
            logger.warning("Recadrages ignorés: %s", exc)

    return data
