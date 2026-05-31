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

# Prompt texte (mode hybride) : la transcription vient déjà d'un ASR local (Whisper).
_PROMPT_TEXT = """\
Yow, Jëf Baay nga — ab jëfandikukat bu xam-xam ci wàll mbey ci Senegaal (Sahel). \
Ab beykat laaj na la (transcription bu ASR), ci wolof :

"{question}"

Tontu ci wolof rekk, bu gàtt te am njariñ. Tontu CI JSON rekk :
{{"response": "<sa tontu ci wolof>"}}"""


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


def _client_candidates():
    """Yield les clients Gemini à essayer. Vertex = 1 client ; clé API = rotation sur 429."""
    if _vertex_enabled():
        try:
            yield genai.Client(
                vertexai=True,
                project=getattr(settings, "GOOGLE_CLOUD_PROJECT"),
                location=getattr(settings, "GEMINI_VERTEX_LOCATION", "us-central1"),
            )
        except Exception as exc:  # noqa: BLE001
            raise GeminiVocalError(f"Init client Vertex échouée : {exc}") from exc
        return
    rotator = _build_rotator()
    for _ in range(len(rotator.keys)):
        yield genai.Client(api_key=rotator.current_key)
        rotator.rotate()  # n'avance qu'au tour suivant (= sur erreur de quota)


def _generate_json(client: "genai.Client", model: str, parts: list) -> dict:
    """Un appel Gemini renvoyant du JSON. Lève GeminiVocalRateLimited sur 429."""
    t0 = time.monotonic()
    try:
        response = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", temperature=0.5,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        if _is_rate_error(exc):
            raise GeminiVocalRateLimited("Quota/limite Gemini atteint.") from exc
        logger.exception("Erreur Gemini")
        raise GeminiVocalError(f"Erreur API Gemini : {exc}") from exc

    duree_ms = int((time.monotonic() - t0) * 1000)
    try:
        data = json.loads((response.text or "").strip())
    except json.JSONDecodeError as exc:
        raise GeminiVocalError("Le modèle n'a pas renvoyé du JSON valide.") from exc
    _log_api(model, duree_ms)
    return data


def _call_with_candidates(model: str, parts: list) -> dict:
    """Essaie les clients (rotation sur quota) jusqu'au premier succès."""
    last: Optional[Exception] = None
    for client in _client_candidates():
        try:
            return _generate_json(client, model, parts)
        except GeminiVocalRateLimited as exc:
            last = exc
            continue
    raise GeminiVocalRateLimited("Quota/limite Gemini atteint sur toutes les clés.") from last


def generate_text(user_text: str, system_text: str = "") -> str:
    """
    Appel Gemini générique texte->texte (sans JSON), utilisé par le pont de
    traduction (LLM agronomique en français). Réutilise la sélection de client
    Vertex/clé-API et la rotation sur 429.
    """
    if not (user_text or "").strip():
        raise GeminiVocalError("Requête vide.")
    model = getattr(settings, "GEMINI_VOCAL_MODEL", "gemini-2.0-flash")
    prompt = f"{system_text.strip()}\n\n{user_text.strip()}" if system_text else user_text.strip()
    parts = [types.Part.from_text(text=prompt)]
    last: Optional[Exception] = None
    for client in _client_candidates():
        try:
            t0 = time.monotonic()
            resp = client.models.generate_content(
                model=model,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(temperature=0.5),
            )
            text = (resp.text or "").strip()
            if not text:
                raise GeminiVocalError("Réponse Gemini vide.")
            _log_api(model, int((time.monotonic() - t0) * 1000))
            return text
        except Exception as exc:  # noqa: BLE001
            if _is_rate_error(exc):
                last = exc
                continue
            raise GeminiVocalError(f"Erreur API Gemini : {exc}") from exc
    raise GeminiVocalRateLimited("Quota/limite Gemini atteint sur toutes les clés.") from last


def process_vocal_wolof(audio_bytes: bytes, mime_type: str = "audio/webm") -> dict:
    """
    Audio Wolof -> {transcript, response} en un seul appel Gemini (audio natif).
    Vertex (région US) si configuré, sinon clé API avec rotation sur 429.
    """
    model = getattr(settings, "GEMINI_VOCAL_MODEL", "gemini-2.0-flash")
    mime = mime_type if mime_type in _GEMINI_AUDIO_MIME else "audio/webm"
    parts = [
        types.Part.from_text(text=_PROMPT),
        types.Part.from_bytes(data=audio_bytes, mime_type=mime),
    ]
    data = _call_with_candidates(model, parts)
    transcript = (data.get("transcript") or "").strip()
    reply = (data.get("response") or "").strip()
    if not reply:
        raise GeminiVocalError("Réponse IA vide (champ 'response' manquant).")
    return {"transcript": transcript, "response": reply}


def generate_response_from_text(transcript: str) -> str:
    """
    Mode hybride : la transcription vient d'un ASR local (Whisper) ; Gemini ne fait
    que générer la réponse agricole Wolof à partir du texte. Retourne la réponse.
    """
    if not (transcript or "").strip():
        raise GeminiVocalError("Transcription vide — rien à traiter.")
    model = getattr(settings, "GEMINI_VOCAL_MODEL", "gemini-2.0-flash")
    parts = [types.Part.from_text(text=_PROMPT_TEXT.format(question=transcript.strip()))]
    data = _call_with_candidates(model, parts)
    reply = (data.get("response") or "").strip()
    if not reply:
        raise GeminiVocalError("Réponse IA vide (champ 'response' manquant).")
    return reply
