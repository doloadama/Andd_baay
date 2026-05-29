"""
Pipeline vocal Wolof via Gemini (remplace l'ancienne voie HuggingFace serverless,
qui ne sert plus les modèles galsenai/*).

Gemini 2.0 Flash accepte l'audio en entrée : un SEUL appel transcrit l'audio Wolof
ET génère la réponse agricole — au lieu des 2-3 appels HF fragiles.

Réutilise le client google.genai et la rotation de clés du module plant_vision.
"""
from __future__ import annotations

import json
import logging
import time
from decimal import Decimal
from typing import Optional

from django.conf import settings
from google import genai
from google.genai import types

from baay.services.plant_vision.key_rotation import GeminiKeyRotator

logger = logging.getLogger(__name__)

# Coût indicatif d'un appel audio Gemini Flash (audio court + réponse texte).
_GEMINI_VOCAL_COST_PER_CALL = Decimal("0.000400")

# MIME audio acceptés par Gemini. webm/opus passe en pratique mais n'est pas
# officiellement documenté ; on le laisse tenter et on gère l'erreur.
_GEMINI_AUDIO_MIME = {
    "audio/wav", "audio/mp3", "audio/mpeg", "audio/aiff",
    "audio/aac", "audio/ogg", "audio/flac", "audio/webm", "audio/mp4",
}

_PROMPT = """\
Yow, Jëf Baay nga — ab jëfandikukat bu xam-xam ci wàll mbey ak mbatiit ci diiwaan \
yi ci Senegaal (Sahel). Dégg nga ab enrégistrement bu ab beykat di wax ci wolof.

Liñ war a def:
1. Transcrire bu wér li nit ki wax, ci wolof.
2. Tontu ci laajam, ci wolof rekk, bu gàtt te am njariñ (mbey, ji, naat, jaaykat, asamaan, mala…).
   Su fekkee enrégistrement bi jaxasoo na walla bañ a leer, indi ab tontu bu rafet ci wolof \
bu ñu ñaan ko mu balluwaat.

Tontu CI JSON rekk, ci xemmeem bii:
{"transcript": "<li mu wax ci wolof>", "response": "<sa tontu ci wolof>"}"""


class GeminiVocalError(Exception):
    """Erreur du pipeline vocal Gemini."""


class GeminiVocalNotConfigured(GeminiVocalError):
    """Clé API Gemini absente."""


class GeminiVocalRateLimited(GeminiVocalError):
    """Quota / limite par minute atteint (429) — transitoire, à retenter."""


def _build_rotator() -> GeminiKeyRotator:
    keys = list(getattr(settings, "GEMINI_API_KEYS", None) or [])
    if not keys:
        single = getattr(settings, "GEMINI_API_KEY", "") or ""
        if single:
            keys = [single]
    if not keys:
        raise GeminiVocalNotConfigured("Clé API Gemini non configurée (GEMINI_API_KEY).")
    return GeminiKeyRotator(keys)


def _log_api(model: str, duree_ms: int, cache_hit: bool = False) -> None:
    try:
        from baay.models import AppelAPILog
        AppelAPILog.objects.create(
            service="gemini",
            modele=model,
            cout_estime_usd=Decimal("0") if cache_hit else _GEMINI_VOCAL_COST_PER_CALL,
            cache_hit=cache_hit,
            duree_ms=duree_ms,
        )
    except Exception:
        logger.debug("AppelAPILog insert échoué (non-bloquant)", exc_info=True)


def process_vocal_wolof(audio_bytes: bytes, mime_type: str = "audio/webm") -> dict:
    """
    Transcrit l'audio Wolof et génère la réponse agricole en un seul appel Gemini.

    Returns:
        {"transcript": "<wolof>", "response": "<wolof>"}
    Raises:
        GeminiVocalNotConfigured : clé absente.
        GeminiVocalError         : échec d'appel ou réponse invalide.
    """
    rotator = _build_rotator()
    model = getattr(settings, "GEMINI_VOCAL_MODEL", "gemini-2.0-flash")
    mime = mime_type if mime_type in _GEMINI_AUDIO_MIME else "audio/webm"

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
                            types.Part.from_text(text=_PROMPT),
                            types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.5,
                ),
            )
            duree_ms = int((time.monotonic() - t0) * 1000)
            raw = (response.text or "").strip()
            data = json.loads(raw)
            transcript = (data.get("transcript") or "").strip()
            reply = (data.get("response") or "").strip()
            if not reply:
                raise GeminiVocalError("Réponse IA vide (champ 'response' manquant).")
            _log_api(model, duree_ms)
            logger.info("Gemini vocal OK (%d ms) — transcript: %s", duree_ms, transcript[:80])
            return {"transcript": transcript, "response": reply}

        except json.JSONDecodeError as exc:
            raise GeminiVocalError("Le modèle n'a pas renvoyé du JSON valide.") from exc
        except GeminiVocalError:
            raise
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            err = str(exc).lower()
            if any(k in err for k in ("429", "resource_exhausted", "quota", "rate")):
                rotator.rotate()
                if rotator.current_key == initial_key:
                    raise GeminiVocalRateLimited(
                        "Quota/limite Gemini atteint sur toutes les clés."
                    ) from exc
                continue
            logger.exception("Erreur Gemini vocal")
            raise GeminiVocalError(f"Erreur API Gemini : {exc}") from exc

    raise GeminiVocalError("Traitement impossible après rotation des clés.") from last_error
