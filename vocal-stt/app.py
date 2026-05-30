"""
Microservice STT Wolof — Faster-Whisper (CTranslate2, CPU).

Expose :
  GET  /health      -> état du service
  POST /transcribe  -> multipart 'audio' (webm/ogg/wav/mp3...) -> {transcript, language, duration_ms}

Conçu pour tourner dans un conteneur Docker sur un VPS CPU. Pas de GPU requis.
"""
from __future__ import annotations

import io
import logging
import os
import time

from fastapi import FastAPI, File, HTTPException, UploadFile
from faster_whisper import WhisperModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wolof-stt")

MODEL_DIR = os.getenv("MODEL_DIR", "/models/whisper-wolof-ct2")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")        # int8 = léger/rapide CPU
BEAM = int(os.getenv("WHISPER_BEAM", "1"))            # 1 = plus rapide sur CPU
LANGUAGE = (os.getenv("WHISPER_LANGUAGE", "") or "").strip() or None  # ex "wo" si supporté, sinon None
MAX_MB = int(os.getenv("WHISPER_MAX_MB", "10"))

app = FastAPI(title="Wolof STT (faster-whisper)", version="1.0")

logger.info("Chargement du modèle %s (device=%s, compute=%s)...", MODEL_DIR, DEVICE, COMPUTE)
model = WhisperModel(MODEL_DIR, device=DEVICE, compute_type=COMPUTE)
logger.info("Modèle chargé.")


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_DIR, "device": DEVICE, "compute": COMPUTE}


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="audio vide")
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"audio > {MAX_MB} Mo")

    t0 = time.monotonic()
    try:
        segments, info = model.transcribe(
            io.BytesIO(data),
            language=LANGUAGE,
            beam_size=BEAM,
            vad_filter=False,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Échec transcription")
        raise HTTPException(status_code=500, detail=f"transcription échouée: {exc}")

    return {
        "transcript": text,
        "language": getattr(info, "language", None),
        "duration_ms": int((time.monotonic() - t0) * 1000),
    }
