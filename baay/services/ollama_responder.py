"""
Client du LLM local via Ollama (FineLlama-3.1-8B Wolof ou tout modèle compatible).

Ollama expose une API OpenAI-compatible en local. Ce service l'appelle pour
générer la réponse agricole Wolof à partir d'un transcript (issu de Whisper local).

Remplace Gemini pour les questions ouvertes quand VOCAL_LLM_BACKEND=ollama.
Résultat : stack 100% auto-hébergeable (Whisper + FAQ + Ollama), zéro cloud.
"""
from __future__ import annotations

import json
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Erreur d'appel au LLM local Ollama."""


class OllamaNotConfigured(OllamaError):
    """URL Ollama ou modèle non configurés."""


# Prompt système Jëf Baay (version texte — Ollama n'a pas d'entrée audio).
_SYSTEM_PROMPT = (
    "Yow Jëf Baay nga, ab jëfandikukat bu xam-xam ci wàll mbey ak mbatiit ci Senegaal (Sahel). "
    "Tontu ci wolof rekk, bu gàtt te am njariñ ci mbey. "
    "Su fekkee laaj bi jëmul ci mbey, wax ko mu balluwaat."
)


def generate_response(transcript: str) -> str:
    """
    Envoie le transcript Wolof au LLM local Ollama et retourne la réponse agricole.

    Settings utilisés :
      OLLAMA_URL       : base URL (ex: http://localhost:11434)
      OLLAMA_MODEL     : nom du modèle (ex: finellama-wolof)
      OLLAMA_TIMEOUT   : timeout en secondes

    Returns:
        Texte de réponse en Wolof.
    Raises:
        OllamaNotConfigured : URL ou modèle absent.
        OllamaError         : service injoignable / réponse vide.
    """
    base = (getattr(settings, "OLLAMA_URL", "") or "").strip().rstrip("/")
    model = (getattr(settings, "OLLAMA_MODEL", "") or "").strip()
    if not base or not model:
        raise OllamaNotConfigured(
            "OLLAMA_URL et OLLAMA_MODEL requis. "
            "Lancez Ollama et renseignez-les dans .env."
        )

    timeout = getattr(settings, "OLLAMA_TIMEOUT", 120)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": transcript.strip()},
        ],
        "stream": False,
        "options": {
            "temperature": 0.6,
            "num_predict": 300,
        },
    }

    t0 = time.monotonic()
    try:
        resp = requests.post(f"{base}/api/chat", json=payload, timeout=timeout)
        resp.raise_for_status()
    except requests.Timeout as exc:
        raise OllamaError(f"Délai dépassé ({timeout}s) en appelant Ollama.") from exc
    except requests.RequestException as exc:
        raise OllamaError(f"Ollama injoignable : {exc}") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise OllamaError("Réponse Ollama non-JSON.") from exc

    reply = (data.get("message", {}).get("content") or "").strip()
    if not reply:
        raise OllamaError("Réponse Ollama vide.")

    ms = int((time.monotonic() - t0) * 1000)
    logger.info("Ollama OK (%d ms, model=%s) — %s", ms, model, reply[:80])

    # Log dans AppelAPILog (coût 0 — local)
    try:
        from decimal import Decimal
        from baay.models import AppelAPILog
        AppelAPILog.objects.create(
            service="ollama", modele=model,
            cout_estime_usd=Decimal("0"), cache_hit=False, duree_ms=ms,
        )
    except Exception:
        pass

    return reply
