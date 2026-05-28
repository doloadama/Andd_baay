import json
import logging
import time
from decimal import Decimal
from typing import Optional

from django.conf import settings
from google import genai
from google.genai import types

from .key_rotation import GeminiKeyRotator
from .prompts import LANGUAGE_INSTRUCTIONS, PLANT_PEST_PROMPT

logger = logging.getLogger(__name__)

# Gemini 2.0 Flash pricing (USD per call estimate — ~2k input + ~500 output tokens)
_GEMINI_FLASH_COST_PER_CALL = Decimal("0.000300")


def _log_api_call(service: str, model: str, cout: Decimal, cache_hit: bool, duree_ms: int) -> None:
    """Enregistre un appel API sans bloquer — les erreurs DB sont silencieuses."""
    try:
        from baay.models import AppelAPILog
        AppelAPILog.objects.create(
            service=service,
            modele=model,
            cout_estime_usd=cout,
            cache_hit=cache_hit,
            duree_ms=duree_ms,
        )
    except Exception:
        logger.debug("AppelAPILog insert failed (non-bloquant)", exc_info=True)


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
    language: str = "fr",
) -> dict:
    """
    Appelle Gemini avec image + prompt JSON structuré.
    Retourne le dict Python parsé depuis la réponse.
    """
    rotator = _build_rotator()
    model = getattr(settings, "PLANT_VISION_MODEL", "gemini-2.0-flash")
    lang_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["fr"])
    prompt = (
        PLANT_PEST_PROMPT
        .replace("{crop_name}", crop_name or "culture")
        .replace("{language_instruction}", lang_instruction)
    )

    initial_key = rotator.current_key
    last_error: Optional[Exception] = None

    for _ in range(len(rotator.keys)):
        api_key = rotator.current_key
        t0 = time.monotonic()
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
            duree_ms = int((time.monotonic() - t0) * 1000)
            raw = response.text or ""
            data = json.loads(raw)
            if not isinstance(data, dict) or "subject" not in data:
                raise PlantVisionGeminiError("Réponse IA invalide (schéma incomplet).")
            _log_api_call("gemini", model, _GEMINI_FLASH_COST_PER_CALL, False, duree_ms)
            return data

        except json.JSONDecodeError as exc:
            raise PlantVisionGeminiError("Le modèle n'a pas renvoyé du JSON valide.") from exc
        except PlantVisionGeminiError:
            raise
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
