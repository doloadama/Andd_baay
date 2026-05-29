"""
Tache Celery — pipeline vocal Wolof asynchrone (Jef Baay).

Moteur : Gemini 2.0 Flash (audio en entree) — transcription + reponse en UN appel.
Remplace l'ancienne voie HuggingFace serverless, qui ne sert plus les modeles
galsenai/* (ASR/LLM/TTS tous "not deployed by any Inference Provider").

La vue enqueue cette tache et repond 202 immediatement ; le front polle le resultat.
TTS (reponse parlee) differe : on renvoie texte + transcription (audio_b64 = None).
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.core.cache import cache

from baay.services.gemini_vocal import (
    GeminiVocalError,
    GeminiVocalNotConfigured,
    process_vocal_wolof,
)

logger = logging.getLogger(__name__)

_RESULT_TTL = 3600  # 1h — duree de vie du resultat de tache dans le cache


@shared_task(bind=True, max_retries=2, default_retry_delay=8)
def process_vocal_task(self, audio_bytes_hex: str, mime: str, task_cache_key: str):
    """
    Traite un enregistrement vocal de maniere asynchrone via Gemini.
    Stocke le resultat dans le cache Django sous task_cache_key :
      {"status": "done",  "result": {transcript, response, audio_b64, tts_available}}
      {"status": "error", "code": "...", "error": "..."}
    """
    try:
        audio_bytes = bytes.fromhex(audio_bytes_hex)

        result = process_vocal_wolof(audio_bytes, mime_type=mime)

        cache.set(task_cache_key, {
            "status": "done",
            "result": {
                "transcript": result.get("transcript", ""),
                "response": result["response"],
                "audio_b64": None,        # TTS differe
                "tts_available": False,
            },
        }, _RESULT_TTL)

    except GeminiVocalNotConfigured:
        cache.set(task_cache_key, {
            "status": "error", "code": "not_configured",
            "error": "Cle API Gemini absente. Ajoutez GEMINI_API_KEY dans votre .env.",
        }, _RESULT_TTL)

    except GeminiVocalError as exc:
        logger.exception("Erreur pipeline vocal Gemini")
        cache.set(task_cache_key, {
            "status": "error", "code": "api_error", "error": str(exc),
        }, _RESULT_TTL)

    except Exception as exc:
        logger.exception("Erreur inattendue process_vocal_task")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            cache.set(task_cache_key, {
                "status": "error", "code": "server_error",
                "error": "Traitement impossible apres plusieurs tentatives. Reessayez.",
            }, _RESULT_TTL)
