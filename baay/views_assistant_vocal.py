"""
Vue de l'assistant vocal Wolof — Jëf Baay.
Pipeline : Audio Wolof → Gemini 2.0 Flash (transcription + réponse) en un appel.
TTS différé. Traitement asynchrone via Celery + polling.
"""
from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_GET
from django.core.cache import cache

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
        ai_configured = bool(
            getattr(settings, "GEMINI_API_KEYS", None)
            or getattr(settings, "GEMINI_API_KEY", "").strip()
        )
        return render(request, "assistant_vocal/index.html", {
            "ai_configured": ai_configured,
            "llm_model": getattr(settings, "GEMINI_VOCAL_MODEL", "gemini-2.0-flash"),
        })

    # ── POST — enqueue asynchrone, retour immédiat (anti-latence 3G) ──────────
    ip = _client_ip(request)
    if not _check_rate(ip):
        return JsonResponse({"error": "rate_limit", "message": "Trop de requêtes. Réessayez dans quelques minutes."}, status=429)

    audio = request.FILES.get("audio")
    if not audio:
        return JsonResponse({"error": "no_audio", "message": "Aucun fichier audio reçu."}, status=400)

    if audio.size > _MAX_AUDIO_MB * 1024 * 1024:
        return JsonResponse({"error": "too_large", "message": f"Audio trop volumineux (max {_MAX_AUDIO_MB} Mo)."}, status=400)

    mime = audio.content_type or "audio/webm"

    # On lit l'audio ici (la requête HTTP a le fichier) puis on délègue au worker.
    from baay.tasks.vocal import process_vocal_task

    task_id = uuid.uuid4().hex
    task_cache_key = f"vocal_task:{task_id}"
    cache.set(task_cache_key, {"status": "pending"}, 3600)

    process_vocal_task.delay(audio.read().hex(), mime, task_cache_key)

    return JsonResponse({
        "status": "pending",
        "task_id": task_id,
        "poll_url": reverse("assistant_vocal_result", args=[task_id]),
    }, status=202)


@require_GET
def assistant_vocal_result(request, task_id: str):
    """
    Polling léger du résultat du pipeline vocal asynchrone.
    Le front interroge cette URL jusqu'à status != "pending".
    """
    data = cache.get(f"vocal_task:{task_id}")
    if data is None:
        return JsonResponse({"status": "expired",
                             "message": "Résultat expiré, réenregistrez votre message."}, status=410)
    return JsonResponse(data)
