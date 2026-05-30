# LLM local Wolof — Ollama + FineLlama-3.1-8B

Réponses agricoles en Wolof **100% local**, sans cloud. Brique LLM de l'assistant
vocal Jëf Baay (architecture hybride : Whisper STT + FAQ locale + LLM Ollama).

## Modèle

[`galsenai/FineLlama-3.1-8B`](https://huggingface.co/galsenai/FineLlama-3.1-8B) —
le seul LLM fine-tuné Wolof. Basé sur Llama 3.1 8B, entraîné par GalsenAI.

## Installation (une seule fois)

### 1. Convertir le modèle HF → GGUF

Le modèle est en format PyTorch (`.bin`). Ollama nécessite du GGUF. Sur ta machine :

```bash
pip install llama-cpp-python huggingface_hub
huggingface-cli download galsenai/FineLlama-3.1-8B --local-dir vocal-llm/models/finellama-hf
python -m llama_cpp.llama_cpp convert-hf-to-gguf vocal-llm/models/finellama-hf \
    --outfile vocal-llm/models/finellama-wolof-q4.gguf \
    --outtype q4_K_M
```

La quantification Q4_K_M réduit le modèle de ~16 Go à ~5 Go, exécutable sur CPU
(~8 Go de RAM requis).

### 2. Lancer Ollama

```bash
docker compose -f vocal-llm/docker-compose.yml up -d
```

### 3. Enregistrer le modèle dans Ollama

```bash
docker exec ollama-wolof ollama create finellama-wolof -f /models/Modelfile
```

Vérifier :
```bash
curl http://localhost:11434/api/chat -d '{"model":"finellama-wolof","messages":[{"role":"user","content":"Naka nga def?"}],"stream":false}'
```

## Brancher Django

Dans le `.env` :
```
VOCAL_LLM_BACKEND=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=finellama-wolof
```

## Performances

| Config | Latence (~300 tokens) | RAM |
|---|---|---|
| CPU (Q4_K_M) | ~10-30 s | ~8 Go |
| GPU NVIDIA (Q4_K_M) | ~2-5 s | ~6 Go VRAM |

Sur CPU, c'est **lent mais acceptable** : la FAQ locale couvre déjà ~80% des
questions instantanément ; Ollama ne traite que les rares questions ouvertes,
et le pipeline est **asynchrone** (l'utilisateur n'attend pas synchrone).

Pour activer le GPU : décommenter la section `deploy.resources` dans `docker-compose.yml`.
