"""
Client LLM via API compatible OpenAI (DeepSeek, Qwen, OpenRouter…).

Génère la réponse agricole Wolof à partir d'un transcript (issu de Whisper local).
Backend « deepseek » de l'assistant vocal — alternative cloud légère à Gemini,
avec des modèles deepseek/qwen souvent gratuits (DeepSeek direct ou OpenRouter).

Endpoint standard OpenAI : POST {base}/chat/completions.
  - DeepSeek direct  : DEEPSEEK_API_URL=https://api.deepseek.com   DEEPSEEK_MODEL=deepseek-chat
  - OpenRouter       : DEEPSEEK_API_URL=https://openrouter.ai/api/v1  DEEPSEEK_MODEL=deepseek/deepseek-chat
"""
from __future__ import annotations

import logging
import time
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class DeepSeekError(Exception):
    """Erreur d'appel au LLM compatible OpenAI."""


class DeepSeekNotConfigured(DeepSeekError):
    """Clé API ou URL non configurées."""


class DeepSeekRateLimited(DeepSeekError):
    """Quota / limite atteint (429) — transitoire."""


_SYSTEM_PROMPT = (
    "Yow Jëf Baay nga, ab jëfandikukat bu xam-xam ci wàll mbey ak mbatiit ci Senegaal (Sahel). "
    "Tontu ci wolof rekk, bu gàtt te am njariñ ci mbey. "
    "Su fekkee laaj bi jëmul ci mbey, wax ko mu balluwaat."
)

# Coût indicatif (DeepSeek-chat ~0.0001-0.0003 $/réponse courte ; 0 si tier gratuit OpenRouter).
_COST_PER_CALL = Decimal("0.000200")


def generate_response(transcript: str) -> str:
    """
    Envoie le transcript Wolof à l'API (DeepSeek/Qwen/OpenRouter) et retourne la réponse.

    Settings :
      DEEPSEEK_API_URL   : base URL (def https://api.deepseek.com)
      DEEPSEEK_API_KEY   : clé Bearer (requis)
      DEEPSEEK_MODEL     : nom du modèle (def deepseek-chat)
      DEEPSEEK_TIMEOUT   : timeout secondes

    Raises:
        DeepSeekNotConfigured : clé absente.
        DeepSeekRateLimited   : 429.
        DeepSeekError         : injoignable / réponse vide.
    """
    if not (transcript or "").strip():
        raise DeepSeekError("Transcription vide — rien à traiter.")

    base = (getattr(settings, "DEEPSEEK_API_URL", "") or "https://api.deepseek.com").strip().rstrip("/")
    key = (getattr(settings, "DEEPSEEK_API_KEY", "") or "").strip()
    model = (getattr(settings, "DEEPSEEK_MODEL", "") or "deepseek-chat").strip()
    if not key:
        raise DeepSeekNotConfigured(
            "DEEPSEEK_API_KEY requis. Créez une clé (DeepSeek ou OpenRouter) et "
            "renseignez-la dans .env."
        )

    timeout = getattr(settings, "DEEPSEEK_TIMEOUT", 60)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": transcript.strip()},
        ],
        "temperature": 0.6,
        "max_tokens": 300,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    t0 = time.monotonic()
    try:
        resp = requests.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=timeout)
    except requests.Timeout as exc:
        raise DeepSeekError(f"Délai dépassé ({timeout}s) en appelant {base}.") from exc
    except requests.RequestException as exc:
        raise DeepSeekError(f"API LLM injoignable : {exc}") from exc

    if resp.status_code == 429:
        raise DeepSeekRateLimited("Quota/limite atteint (429).")
    if resp.status_code in (401, 403):
        raise DeepSeekError(f"Auth refusée (HTTP {resp.status_code}) — clé invalide.")
    if not resp.ok:
        raise DeepSeekError(f"Erreur API ({resp.status_code}) : {(resp.text or '')[:120]}")

    try:
        data = resp.json()
        reply = (data["choices"][0]["message"]["content"] or "").strip()
    except (ValueError, KeyError, IndexError) as exc:
        raise DeepSeekError("Réponse API inattendue.") from exc

    if not reply:
        raise DeepSeekError("Réponse LLM vide.")

    ms = int((time.monotonic() - t0) * 1000)
    logger.info("DeepSeek/OpenAI-compat OK (%d ms, model=%s) — %s", ms, model, reply[:80])

    try:
        from baay.models import AppelAPILog
        AppelAPILog.objects.create(
            service="deepseek", modele=model,
            cout_estime_usd=_COST_PER_CALL, cache_hit=False, duree_ms=ms,
        )
    except Exception:
        pass

    return reply
