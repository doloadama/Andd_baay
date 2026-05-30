# Microservice STT Wolof — Faster-Whisper

Transcription Wolof **locale, sur CPU, hors-ligne**, sans coût par appel ni cold start cloud.
Brique STT de l'assistant vocal Jëf Baay (architecture hybride : STT local + réponse Gemini).

## Modèle

Par défaut : [`M9and2M/whisper-small-wolof`](https://huggingface.co/M9and2M/whisper-small-wolof)
(fine-tune de `openai/whisper-small`, WER ~0.17, 57 h d'entraînement).
Converti en CTranslate2 (`int8`) au build pour faster-whisper.

Autres candidats (changer `WHISPER_HF_MODEL`) :
`serge-wilson/whisper-small-wolof`, `cifope/whisper-small-wolof`, `cibfaye/whisper-wolof`.

## Démarrage

```bash
docker compose -f vocal-stt/docker-compose.yml up -d --build
# 1er build : télécharge + convertit le modèle (quelques minutes).
curl http://localhost:9000/health
```

Test de transcription :
```bash
curl -F "audio=@mon_audio.wav" http://localhost:9000/transcribe
# -> {"transcript": "...", "language": "...", "duration_ms": 1234}
```

## Brancher Django

Dans le `.env` du projet :
```
VOCAL_STT_BACKEND=whisper_local
WHISPER_STT_URL=http://localhost:9000      # ou l'URL interne du VPS/conteneur
```
La tâche `process_vocal_task` utilise alors : Whisper local (transcription) → Gemini (réponse).
Avec `VOCAL_STT_BACKEND=gemini` (défaut), tout passe par Gemini (audio natif).

## Réglages (env)

| Variable | Défaut | Rôle |
|---|---|---|
| `WHISPER_HF_MODEL` (build arg) | `M9and2M/whisper-small-wolof` | modèle source HF |
| `QUANTIZATION` (build arg) | `int8` | quantification CT2 |
| `WHISPER_COMPUTE` | `int8` | `int8` (CPU) / `float16` (GPU) |
| `WHISPER_BEAM` | `1` | beam search (1 = rapide) |
| `WHISPER_LANGUAGE` | (vide) | forcer la langue ; laisser vide pour un fine-tune Wolof |
| `WHISPER_MAX_MB` | `10` | taille audio max |

## Notes perf

- `whisper-small` int8 sur CPU : ~1-3 s pour un clip de 10 s. La concurrence consomme
  des cœurs → dimensionner le VPS / lancer plusieurs workers uvicorn (`--workers N`).
- Pour plus de précision : passer à un fine-tune `medium` (plus lent, plus de RAM).
