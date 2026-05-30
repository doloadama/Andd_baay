"""
Client du microservice STT local (Faster-Whisper Wolof).

Le modèle tourne dans un conteneur Docker dédié (voir dossier vocal-stt/) exposant
POST /transcribe. Avantage : transcription Wolof dédiée, sur CPU, hors-ligne,
zéro coût par appel, pas de cold start cloud.
"""
from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class WhisperLocalError(Exception):
    """Échec d'appel au service STT local."""


class WhisperLocalNotConfigured(WhisperLocalError):
    """URL du service STT non configurée."""


def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
    """
    Envoie l'audio au microservice Faster-Whisper et retourne la transcription Wolof.

    Raises:
        WhisperLocalNotConfigured : WHISPER_STT_URL absent.
        WhisperLocalError         : service injoignable / réponse vide.
    """
    base = (getattr(settings, "WHISPER_STT_URL", "") or "").strip().rstrip("/")
    if not base:
        raise WhisperLocalNotConfigured(
            "WHISPER_STT_URL non configurée. Démarrez le conteneur vocal-stt et "
            "renseignez WHISPER_STT_URL dans .env (ex: http://localhost:9000)."
        )
    timeout = getattr(settings, "WHISPER_STT_TIMEOUT", 60)
    files = {"audio": ("audio", audio_bytes, mime_type or "application/octet-stream")}
    try:
        resp = requests.post(f"{base}/transcribe", files=files, timeout=timeout)
        resp.raise_for_status()
    except requests.Timeout as exc:
        raise WhisperLocalError("Délai dépassé en appelant le STT local.") from exc
    except requests.RequestException as exc:
        raise WhisperLocalError(f"Service STT local injoignable : {exc}") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise WhisperLocalError("Réponse STT non-JSON.") from exc

    transcript = (data.get("transcript") or "").strip()
    if not transcript:
        raise WhisperLocalError("Transcription vide renvoyée par le STT local.")
    logger.info("Whisper local OK (%s ms) — %s",
                data.get("duration_ms", "?"), transcript[:80])
    return transcript
