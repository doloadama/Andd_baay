# ── Microservice STT Wolof (Faster-Whisper / CTranslate2, CPU) ──────────────
# Multi-stage : on convertit le modèle HF Whisper-Wolof en format CTranslate2
# dans un builder (qui tire torch+transformers), puis on copie le modèle
# converti dans une image runtime légère (sans torch).

# ---------- Stage 1 : conversion du modèle ----------
FROM python:3.11-slim AS builder

ARG WHISPER_HF_MODEL=M9and2M/whisper-small-wolof
ARG QUANTIZATION=int8

RUN pip install --no-cache-dir "ctranslate2>=4.0" "transformers>=4.40" torch --extra-index-url https://download.pytorch.org/whl/cpu

# Convertit le modèle HF -> CTranslate2 (téléchargé depuis le Hub au build).
RUN ct2-transformers-converter \
    --model ${WHISPER_HF_MODEL} \
    --output_dir /models/whisper-wolof-ct2 \
    --quantization ${QUANTIZATION} \
    --copy_files tokenizer.json preprocessor_config.json \
    || ct2-transformers-converter --model ${WHISPER_HF_MODEL} --output_dir /models/whisper-wolof-ct2 --quantization ${QUANTIZATION}

# ---------- Stage 2 : runtime léger ----------
FROM python:3.11-slim AS runtime

# ffmpeg pour décoder webm/ogg/mp3 (PyAV s'appuie dessus pour certains formats).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=builder /models /models
COPY app.py .

ENV MODEL_DIR=/models/whisper-wolof-ct2 \
    WHISPER_DEVICE=cpu \
    WHISPER_COMPUTE=int8 \
    WHISPER_BEAM=1

EXPOSE 9000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9000"]
