"""
GalsenAI HuggingFace Inference API — pipeline vocal Wolof.

Modèles utilisés :
  ASR  : galsenai/whisper-large-v3-wo
  LLM  : galsenai/FineLlama-3.1-8B
  TTS  : galsenai/xTTS-v2-wolof

Tous appelés via l'API Inference serverless HuggingFace.
Le token HF_API_TOKEN doit être configuré dans .env.

Cold start note : les modèles serverless peuvent mettre jusqu'à 20s à démarrer.
L'API retourne HTTP 503 + {"estimated_time": N} pendant ce temps.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

HF_BASE = "https://api-inference.huggingface.co/models"
_MAX_COLD_RETRIES = 3
_COLD_WAIT = 12  # secondes entre chaque retry sur cold start


class GalsenAIError(Exception):
    """Erreur pipeline GalsenAI."""


class GalsenAINotConfigured(GalsenAIError):
    """Token HF manquant."""


class GalsenAIModelLoading(GalsenAIError):
    """Modèle en cours de chargement — réessayer dans quelques secondes."""

    def __init__(self, estimated_time: float = 20.0):
        self.estimated_time = estimated_time
        super().__init__(f"Modèle en cours de chargement, réessayez dans {estimated_time:.0f}s.")


def _token() -> str:
    tok = getattr(settings, "HF_API_TOKEN", "").strip()
    if not tok:
        raise GalsenAINotConfigured(
            "HF_API_TOKEN manquant. Ajoutez-le dans votre .env."
        )
    return tok


def _headers(content_type: str = "application/json") -> dict:
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": content_type,
    }


def _post_with_retry(
    url: str,
    *,
    json_body: Optional[dict] = None,
    raw_body: Optional[bytes] = None,
    content_type: str = "application/json",
    timeout: int | None = None,
) -> requests.Response:
    """POST avec gestion du cold start (503 + estimated_time)."""
    effective_timeout = timeout or getattr(settings, "GALSENAI_TIMEOUT", 60)
    headers = _headers(content_type)

    for attempt in range(_MAX_COLD_RETRIES):
        try:
            if raw_body is not None:
                resp = requests.post(url, headers=headers, data=raw_body, timeout=effective_timeout)
            else:
                resp = requests.post(url, headers=headers, json=json_body, timeout=effective_timeout)
        except requests.Timeout:
            raise GalsenAIError("Timeout dépassé en appelant l'API GalsenAI.")
        except requests.RequestException as exc:
            raise GalsenAIError(f"Erreur réseau : {exc}") from exc

        if resp.status_code == 503:
            body = resp.json() if resp.content else {}
            est = float(body.get("estimated_time", _COLD_WAIT))
            if attempt < _MAX_COLD_RETRIES - 1:
                logger.info("GalsenAI cold start, attente %.0fs (tentative %d)", est, attempt + 1)
                time.sleep(min(est, _COLD_WAIT))
                continue
            raise GalsenAIModelLoading(est)

        if resp.status_code == 401:
            raise GalsenAIError("Token HuggingFace invalide ou expiré.")

        if not resp.ok:
            msg = resp.text[:200] if resp.text else f"HTTP {resp.status_code}"
            raise GalsenAIError(f"Erreur API GalsenAI ({resp.status_code}) : {msg}")

        return resp

    raise GalsenAIError("Impossible de joindre l'API GalsenAI après plusieurs tentatives.")


# ──────────────────────────────────────────────────────────────────────────────
# 1. ASR — Transcription audio Wolof
# ──────────────────────────────────────────────────────────────────────────────

def transcribe_wolof(audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
    """
    Transcrit de l'audio Wolof en texte via galsenai/whisper-large-v3-wo.

    Args:
        audio_bytes : contenu binaire du fichier audio
        mime_type   : type MIME (audio/webm, audio/wav, audio/mpeg…)

    Returns:
        Texte transcrit en Wolof.
    """
    model = getattr(settings, "GALSENAI_ASR_MODEL", "galsenai/whisper-large-v3-wo")
    url = f"{HF_BASE}/{model}"
    logger.info("GalsenAI ASR → %s (%d bytes, %s)", model, len(audio_bytes), mime_type)

    resp = _post_with_retry(url, raw_body=audio_bytes, content_type=mime_type)
    data = resp.json()

    if isinstance(data, dict) and "text" in data:
        return data["text"].strip()
    if isinstance(data, list) and data and "text" in data[0]:
        return data[0]["text"].strip()

    raise GalsenAIError(f"Réponse ASR inattendue : {str(data)[:200]}")


# ──────────────────────────────────────────────────────────────────────────────
# 2. LLM — Génération réponse agricole en Wolof
# ──────────────────────────────────────────────────────────────────────────────

_AGRI_PROMPT_WO = """\
Yow, Jëf Baay la — ab juróom bu ñuy jëfandikoo ci diggante jën ak yonent ci Senegaal. \
Def ab tontu bu mucc, bu xoluwaay, ci wolof, ci këf bi xam-xam serer yëgël ak mbey. \
Am ñu ñaan wolof ci ab laaj bu mbey :

Question : {question}

Tontu ci wolof (di naan gis gis ci mbey) :"""

# Fallback français si la réponse LLM est vide
_AGRI_PROMPT_FR_FALLBACK = """\
Tu es Jëf Baay, un assistant agricole expert pour les zones sahéliennes du Sénégal. \
Réponds de façon concise et pratique en wolof à cette question d'un agriculteur :

Question : {question}

Réponse en wolof :"""


def generate_wolof_response(transcript: str, max_tokens: int = 400) -> str:
    """
    Génère une réponse agricole en Wolof via galsenai/FineLlama-3.1-8B.

    Args:
        transcript  : texte transcrit de la question de l'agriculteur (Wolof)
        max_tokens  : longueur max de la réponse

    Returns:
        Texte de réponse en Wolof.
    """
    model = getattr(settings, "GALSENAI_LLM_MODEL", "galsenai/FineLlama-3.1-8B")
    url = f"{HF_BASE}/{model}"

    prompt = _AGRI_PROMPT_WO.format(question=transcript.strip())
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": 0.65,
            "do_sample": True,
            "return_full_text": False,
        },
    }
    logger.info("GalsenAI LLM → %s (%d chars question)", model, len(transcript))

    resp = _post_with_retry(url, json_body=payload)
    data = resp.json()

    if isinstance(data, list) and data:
        text = data[0].get("generated_text", "").strip()
        if text:
            return text

    if isinstance(data, dict) and "generated_text" in data:
        return data["generated_text"].strip()

    raise GalsenAIError(f"Réponse LLM inattendue : {str(data)[:200]}")


# ──────────────────────────────────────────────────────────────────────────────
# 3. TTS — Synthèse vocale Wolof
# ──────────────────────────────────────────────────────────────────────────────

def synthesize_wolof(text: str) -> bytes | None:
    """
    Synthétise du texte Wolof en audio via galsenai/xTTS-v2-wolof.

    Returns:
        Octets audio (wav/mp3), ou None si le modèle n'est pas disponible.
    """
    model = getattr(settings, "GALSENAI_TTS_MODEL", "galsenai/xTTS-v2-wolof")
    url = f"{HF_BASE}/{model}"
    payload = {"inputs": text.strip()}
    logger.info("GalsenAI TTS → %s (%d chars)", model, len(text))

    try:
        resp = _post_with_retry(url, json_body=payload)
        content_type = resp.headers.get("Content-Type", "")
        if "audio" in content_type or "octet-stream" in content_type:
            return resp.content
        # Si JSON retourné (erreur ou format diff), loguer et retourner None
        logger.warning("GalsenAI TTS: réponse non-audio (%s): %s", content_type, resp.text[:100])
        return None
    except GalsenAIModelLoading:
        logger.info("GalsenAI TTS: modèle en chargement, TTS ignoré pour cette requête.")
        return None
    except GalsenAIError as exc:
        logger.warning("GalsenAI TTS indisponible : %s", exc)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# 4. Traduction — pont NLLB Wolof ↔ Français
# ──────────────────────────────────────────────────────────────────────────────

def _translate(text: str, *, direction: str) -> str:
    """
    Traduit via galsenai/wolof-To-French-Translator (NLLB, bidirectionnel).

    Args:
        text      : texte source.
        direction : "wo2fr" (wolof→français) ou "fr2wo" (français→wolof).

    Returns:
        Texte traduit. Lève GalsenAIError en cas d'échec (l'appelant décide du repli).
    """
    text = (text or "").strip()
    if not text:
        return ""
    model = getattr(settings, "GALSENAI_TRAD_MODEL", "galsenai/wolof-To-French-Translator")
    url = f"{HF_BASE}/{model}"
    # NLLB attend des codes de langue ; le modèle galsenai expose src/tgt via parameters.
    src, tgt = ("wol_Latn", "fra_Latn") if direction == "wo2fr" else ("fra_Latn", "wol_Latn")
    payload = {"inputs": text, "parameters": {"src_lang": src, "tgt_lang": tgt}}
    logger.info("GalsenAI TRAD %s → %s (%d chars)", direction, model, len(text))

    resp = _post_with_retry(url, json_body=payload)
    data = resp.json()
    # Format HF translation : [{"translation_text": "..."}]
    if isinstance(data, list) and data and "translation_text" in data[0]:
        return data[0]["translation_text"].strip()
    if isinstance(data, dict) and "translation_text" in data:
        return data["translation_text"].strip()
    if isinstance(data, list) and data and "generated_text" in data[0]:
        return data[0]["generated_text"].strip()
    raise GalsenAIError(f"Réponse traduction inattendue : {str(data)[:200]}")


def wolof_to_french(text: str) -> str:
    """Wolof → Français (pont NLLB). Lève GalsenAIError si l'API échoue."""
    return _translate(text, direction="wo2fr")


def french_to_wolof(text: str) -> str:
    """Français → Wolof (pont NLLB). Lève GalsenAIError si l'API échoue."""
    return _translate(text, direction="fr2wo")
