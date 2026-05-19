import json
import logging
from typing import Optional

from django.conf import settings
from google import genai
from google.genai import types

from .key_rotation import GeminiKeyRotator
from .prompts import PLANT_PEST_PROMPT

logger = logging.getLogger(__name__)


class PlantVisionGeminiError(Exception):
    """Erreur d'appel Gemini pour l'analyse visuelle."""


def _build_rotator() -> GeminiKeyRotator:
    keys = list(getattr(settings, "GEMINI_API_KEYS", None) or [])
    if not keys:
        single = getattr(settings, "GEMINI_API_KEY", "") or ""
        if single:
            keys = [single]
    if not keys:
        raise PlantVisionGeminiError("Clé API Gemini non configurée.")
    return GeminiKeyRotator(keys)


def call_gemini_vision(
    image_bytes: bytes,
    mime_type: str,
    *,
    crop_name: str = "",
) -> dict:
    """
    Appelle Gemini avec image + prompt JSON structuré.
    Retourne le dict Python parsé depuis la réponse.
    """
    rotator = _build_rotator()
    model = getattr(settings, "PLANT_VISION_MODEL", "gemini-2.0-flash")
    prompt = PLANT_PEST_PROMPT.replace("{crop_name}", crop_name or "culture")

    initial_key = rotator.current_key
    last_error: Optional[Exception] = None

    for _ in range(len(rotator.keys)):
        api_key = rotator.current_key
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=prompt),
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            raw = response.text or ""
            data = json.loads(raw)
            if not isinstance(data, dict) or "subject" not in data:
                raise PlantVisionGeminiError("Réponse IA invalide (schéma incomplet).")
            return data

        except json.JSONDecodeError as exc:
            raise PlantVisionGeminiError("Le modèle n'a pas renvoyé du JSON valide.") from exc
        except Exception as exc:
            last_error = exc
            err = str(exc).lower()
            if "429" in err or "resource_exhausted" in err or "quota" in err or "rate" in err:
                rotator.rotate()
                if rotator.current_key == initial_key:
                    raise PlantVisionGeminiError(
                        "Quota Gemini dépassé sur toutes les clés disponibles."
                    ) from exc
                continue
            logger.exception("Erreur Gemini vision")
            raise PlantVisionGeminiError(f"Erreur API Gemini: {exc}") from exc

    raise PlantVisionGeminiError("Analyse impossible après rotation des clés.") from last_error
