"""
Vue de l'assistant vocal Wolof — Jëf Baay.
Pipeline : Audio → ASR Wolof → FineLlama-3.1-8B → (TTS optionnel).
"""
from __future__ import annotations

import base64
import logging

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
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

_RATE_LIMIT = 10
_RATE_WINDOW = 600
_MAX_AUDIO_MB = 5
_ALLOWED_MIME = {
    "audio/webm", "audio/wav", "audio/mpeg", "audio/ogg",
    "audio/mp4", "audio/x-m4a",
}


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _check_rate(ip: str) -> bool:
    key = f"vocal_rl:{ip}"
    count = cache.get(key, 0)
    if count >= _RATE_LIMIT:
        return False
    cache.set(key, count + 1, _RATE_WINDOW)
    return True


@require_http_methods(["GET", "POST"])
def assistant_vocal(request):
    if request.method == "GET":
        hf_configured = bool(getattr(settings, "HF_API_TOKEN", "").strip())
        return render(request, "assistant_vocal/index.html", {
            "hf_configured": hf_configured,
            "llm_model": getattr(settings, "GALSENAI_LLM_MODEL", "galsenai/FineLlama-3.1-8B"),
        })

    # ── POST — traitement audio ──────────────────────────────────────────────
    ip = _client_ip(request)
    if not _check_rate(ip):
        return JsonResponse({"error": "rate_limit", "message": "Trop de requêtes. Réessayez dans quelques minutes."}, status=429)

    audio = request.FILES.get("audio")
    if not audio:
        return JsonResponse({"error": "no_audio", "message": "Aucun fichier audio reçu."}, status=400)

    if audio.size > _MAX_AUDIO_MB * 1024 * 1024:
        return JsonResponse({"error": "too_large", "message": f"Audio trop volumineux (max {_MAX_AUDIO_MB} Mo)."}, status=400)

    mime = audio.content_type or "audio/webm"

    try:
        audio_bytes = audio.read()

        # Étape 1 : ASR Wolof
        transcript = transcribe_wolof(audio_bytes, mime_type=mime)
        logger.info("ASR transcript: %s", transcript[:120])

        # Étape 2 : LLM — réponse agricole en Wolof
        response_text = generate_wolof_response(transcript)
        logger.info("LLM response: %s", response_text[:120])

        # Étape 3 : TTS (optionnel — ne bloque pas si indisponible)
        audio_b64 = None
        tts_bytes = synthesize_wolof(response_text)
        if tts_bytes:
            audio_b64 = base64.b64encode(tts_bytes).decode()

        return JsonResponse({
            "status": "ok",
            "transcript": transcript,
            "response": response_text,
            "audio_b64": audio_b64,
            "tts_available": audio_b64 is not None,
        })

    except GalsenAINotConfigured:
        return JsonResponse({
            "error": "not_configured",
            "message": "Token HuggingFace manquant. Ajoutez HF_API_TOKEN dans votre .env.",
        }, status=503)

    except GalsenAIModelLoading as exc:
        return JsonResponse({
            "error": "model_loading",
            "message": f"Le modèle démarre — réessayez dans {exc.estimated_time:.0f} secondes.",
            "estimated_time": exc.estimated_time,
        }, status=503)

    except GalsenAIError as exc:
        logger.exception("Erreur GalsenAI pipeline")
        return JsonResponse({"error": "api_error", "message": str(exc)}, status=502)

    except Exception:
        logger.exception("Erreur inattendue assistant_vocal")
        return JsonResponse({"error": "server_error", "message": "Erreur interne. Réessayez."}, status=500)
