"""
Tache Celery — pipeline vocal Wolof asynchrone (Jef Baay).

Pipeline : Audio -> ASR Wolof -> LLM (FineLlama) -> TTS (optionnel).
Sort le traitement bloquant (cold start HuggingFace ~12s) de la requete HTTP :
la vue enqueue et repond 202 immediatement, le front polle le resultat.

Calque sur baay/tasks/diagnostic.py (meme contrat de cache + AppelAPILog).
"""
from __future__ import annotations

import base64
import hashlib
import logging
import time
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from baay.services.galsenai_service import (
    GalsenAIError,
    GalsenAIModelLoading,
    GalsenAINotConfigured,
    generate_wolof_response,
    synthesize_wolof,
    transcribe_wolof,
)

logger = logging.getLogger(__name__)

# Cache reponse LLM par question normalisee (questions agricoles recurrentes).
_QUESTION_TTL = 60 * 60 * 24 * 30  # 30 jours
_RESULT_TTL = 3600                  # 1h — duree de vie du resultat de tache


def _log_api(cache_hit: bool, duree_ms: int) -> None:
    """Journalise l'appel pour le monitoring des couts (modele AppelAPILog)."""
    try:
        from baay.models import AppelAPILog

        AppelAPILog.objects.create(
            service=AppelAPILog.SERVICE_GALSENAI,
            modele=getattr(settings, "GALSENAI_LLM_MODEL", ""),
            cache_hit=cache_hit,
            duree_ms=duree_ms,
            cout_estime_usd=Decimal("0"),
        )
    except Exception:  # journalisation best-effort, ne bloque jamais le pipeline
        logger.debug("AppelAPILog non enregistre", exc_info=True)


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def process_vocal_task(self, audio_bytes_hex: str, mime: str, task_cache_key: str):
    """
    Traite un enregistrement vocal de maniere asynchrone.
    Stocke le resultat dans le cache Django sous task_cache_key :
      {"status": "done",    "result": {...}}
      {"status": "error",   "code": "...", "error": "..."}
    """
    t0 = time.monotonic()
    try:
        audio_bytes = bytes.fromhex(audio_bytes_hex)

        # Etape 1 : ASR Wolof
        transcript = transcribe_wolof(audio_bytes, mime_type=mime)
        logger.info("ASR transcript: %s", transcript[:120])

        # Etape 2 : LLM — cache par question normalisee
        norm = " ".join(transcript.lower().split())
        qkey = f"vocal_q:{hashlib.sha256(norm.encode()).hexdigest()}"
        cached_reply = cache.get(qkey) if norm else None
        if cached_reply is not None:
            response_text = cached_reply
            logger.info("process_vocal_task: cache hit (question)")
            _log_api(cache_hit=True, duree_ms=int((time.monotonic() - t0) * 1000))
        else:
            response_text = generate_wolof_response(transcript)
            if norm:
                cache.set(qkey, response_text, _QUESTION_TTL)
            _log_api(cache_hit=False, duree_ms=int((time.monotonic() - t0) * 1000))
        logger.info("LLM response: %s", response_text[:120])

        # Etape 3 : TTS (DIFFERE — desactive par defaut via GALSENAI_TTS_ENABLED).
        # Le TTS Wolof est le maillon le plus fragile : on livre d'abord texte +
        # transcription. Reactiver en mettant GALSENAI_TTS_ENABLED=true une fois
        # un modele TTS fiable confirme.
        audio_b64 = None
        if getattr(settings, "GALSENAI_TTS_ENABLED", False):
            try:
                tts_bytes = synthesize_wolof(response_text)
                if tts_bytes:
                    audio_b64 = base64.b64encode(tts_bytes).decode()
            except Exception:
                logger.warning("TTS indisponible, reponse texte seule", exc_info=True)

        cache.set(task_cache_key, {
            "status": "done",
            "result": {
                "transcript": transcript,
                "response": response_text,
                "audio_b64": audio_b64,
                "tts_available": audio_b64 is not None,
            },
        }, _RESULT_TTL)

    except GalsenAINotConfigured:
        cache.set(task_cache_key, {
            "status": "error", "code": "not_configured",
            "error": "Token HuggingFace manquant. Ajoutez HF_API_TOKEN dans votre .env.",
        }, _RESULT_TTL)

    except GalsenAIModelLoading as exc:
        # Cold start HF : on attend cote worker (pas cote utilisateur) puis on relance.
        logger.info("Modele HF en chargement, retry dans %.0fs", exc.estimated_time)
        try:
            raise self.retry(exc=exc, countdown=max(5, int(exc.estimated_time)))
        except self.MaxRetriesExceededError:
            cache.set(task_cache_key, {
                "status": "error", "code": "model_loading",
                "error": "Le modele n'a pas demarre a temps. Reessayez dans une minute.",
            }, _RESULT_TTL)

    except GalsenAIError as exc:
        logger.exception("Erreur GalsenAI pipeline")
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
