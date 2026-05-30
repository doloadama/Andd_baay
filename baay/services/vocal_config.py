from __future__ import annotations

from django.conf import settings


TEXT_ONLY_LLM_BACKENDS = frozenset({"ollama", "deepseek"})


def vocal_llm_backend() -> str:
    return (getattr(settings, "VOCAL_LLM_BACKEND", "gemini") or "gemini").strip().lower()


def effective_stt_backend() -> str:
    stt_backend = (getattr(settings, "VOCAL_STT_BACKEND", "gemini") or "gemini").strip().lower()
    if stt_backend != "whisper_local" and vocal_llm_backend() in TEXT_ONLY_LLM_BACKENDS:
        return "whisper_local"
    return stt_backend


def gemini_configured() -> bool:
    return bool(
        getattr(settings, "GEMINI_API_KEYS", None)
        or (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
        or (
            getattr(settings, "GEMINI_USE_VERTEX", False)
            and (getattr(settings, "GOOGLE_CLOUD_PROJECT", "") or "").strip()
        )
    )


def vocal_ai_configured() -> bool:
    stt_backend = effective_stt_backend()
    llm_backend = vocal_llm_backend()

    if stt_backend != "whisper_local":
        return gemini_configured()

    if not (getattr(settings, "WHISPER_STT_URL", "") or "").strip():
        return False

    if llm_backend == "ollama":
        return bool(
            (getattr(settings, "OLLAMA_URL", "") or "").strip()
            and (getattr(settings, "OLLAMA_MODEL", "") or "").strip()
        )
    if llm_backend == "deepseek":
        return bool((getattr(settings, "DEEPSEEK_API_KEY", "") or "").strip())
    return gemini_configured()


def vocal_model_label() -> str:
    llm_backend = vocal_llm_backend()
    if llm_backend == "ollama":
        return (getattr(settings, "OLLAMA_MODEL", "") or "Ollama local").strip()
    if llm_backend == "deepseek":
        return (getattr(settings, "DEEPSEEK_MODEL", "") or "deepseek-chat").strip()
    return (getattr(settings, "GEMINI_VOCAL_MODEL", "") or "gemini-2.0-flash").strip()
