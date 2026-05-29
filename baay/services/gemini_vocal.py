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


def _vertex_enabled() -> bool:
    return bool(
        getattr(settings, "GEMINI_USE_VERTEX", False)
        and getattr(settings, "GOOGLE_CLOUD_PROJECT", "")
    )


def _is_rate_error(exc: Exception) -> bool:
    err = str(exc).lower()
    return any(k in err for k in ("429", "resource_exhausted", "quota", "rate"))


def _run(client: "genai.Client", model: str, audio_bytes: bytes, mime: str) -> dict:
    """Un appel Gemini : audio -> {transcript, response}. Lève GeminiVocalRateLimited sur 429."""
    t0 = time.monotonic()
    try:
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
    except Exception as exc:  # noqa: BLE001
        if _is_rate_error(exc):
            raise GeminiVocalRateLimited("Quota/limite Gemini atteint.") from exc
        logger.exception("Erreur Gemini vocal")
        raise GeminiVocalError(f"Erreur API Gemini : {exc}") from exc

    duree_ms = int((time.monotonic() - t0) * 1000)
    try:
        data = json.loads((response.text or "").strip())
    except json.JSONDecodeError as exc:
        raise GeminiVocalError("Le modèle n'a pas renvoyé du JSON valide.") from exc
    transcript = (data.get("transcript") or "").strip()
    reply = (data.get("response") or "").strip()
    if not reply:
        raise GeminiVocalError("Réponse IA vide (champ 'response' manquant).")
    _log_api(model, duree_ms)
    logger.info("Gemini vocal OK (%d ms, %s) — transcript: %s",
                duree_ms, "vertex" if _vertex_enabled() else "api-key", transcript[:80])
    return {"transcript": transcript, "response": reply}


def process_vocal_wolof(audio_bytes: bytes, mime_type: str = "audio/webm") -> dict:
    """
    Transcrit l'audio Wolof et génère la réponse agricole en un seul appel Gemini.

    Deux modes (sélection auto) :
      - Vertex AI (GEMINI_USE_VERTEX=true + GOOGLE_CLOUD_PROJECT) : région forcée
        (us-central1 par défaut), auth ADC/service account — contourne le quota UE.
      - Clé API (sinon) : rotation des clés GEMINI_API_KEYS sur 429.

    Returns:
        {"transcript": "<wolof>", "response": "<wolof>"}
    Raises:
        GeminiVocalNotConfigured : ni Vertex ni clé configurés.
        GeminiVocalRateLimited   : quota/limite atteint.
        GeminiVocalError         : échec d'appel ou réponse invalide.
    """
    model = getattr(settings, "GEMINI_VOCAL_MODEL", "gemini-2.0-flash")
    mime = mime_type if mime_type in _GEMINI_AUDIO_MIME else "audio/webm"

    # ── Mode Vertex AI (région US) ──────────────────────────────────────────
    if _vertex_enabled():
        try:
            client = genai.Client(
                vertexai=True,
                project=getattr(settings, "GOOGLE_CLOUD_PROJECT"),
                location=getattr(settings, "GEMINI_VERTEX_LOCATION", "us-central1"),
            )
        except Exception as exc:  # noqa: BLE001
            raise GeminiVocalError(f"Init client Vertex échouée : {exc}") from exc
        return _run(client, model, audio_bytes, mime)

    # ── Mode clé API (avec rotation sur 429) ────────────────────────────────
    rotator = _build_rotator()
    initial_key = rotator.current_key
    last_error: Optional[Exception] = None
    for _ in range(len(rotator.keys)):
        try:
            client = genai.Client(api_key=rotator.current_key)
            return _run(client, model, audio_bytes, mime)
        except GeminiVocalRateLimited as exc:
            last_error = exc
            rotator.rotate()
            if rotator.current_key == initial_key:
                raise GeminiVocalRateLimited(
                    "Quota/limite Gemini atteint sur toutes les clés."
                ) from exc
            continue
    raise GeminiVocalError("Traitement impossible après rotation des clés.") from last_error
