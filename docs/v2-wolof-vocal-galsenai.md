# V2 — Interface vocale Wolof (GalsenAI)

> Idée actée lors du sprint mai 2026. À implémenter en V2.
> Contexte : les agriculteurs non-lettrés constituent la majorité des utilisateurs cibles.
> Le Wolof est parlé par ~95% de la population sénégalaise (1re ou 2e langue).

---

## Pourquoi GalsenAI

La communauté [GalsenAI Lab](https://huggingface.co/galsenai) a adopté une approche pragmatique :
**fine-tuning de LLMs open source** (Meta Llama, OpenAI Whisper, Coqui xTTS) sur un corpus
Wolof de qualité, vérifié par des linguistes via la plateforme participative
[Waxal](https://waxal.galsen.ai) (dataset WaxalNLP).

---

## Modèles disponibles sur HuggingFace `galsenai/`

| Tâche | Modèle | Base | Notes |
|---|---|---|---|
| **LLM chat** | `FineLlama-3.1-8B` | Llama 3.1 | Génération texte Wolof |
| **LLM Q&A** | `llama-2-7B_wolof_qa_assistant` | Llama 2 | Assistant conversationnel |
| **LLM base** | `llama2-7B_wolof` | Llama 2 | Complétion / compréhension |
| **Traduction** | `wolof-To-French-Translator` | NLLB (Meta) | Wo↔Fr bidirectionnel |
| **ASR** | `whisper-large-v3-wo` | Whisper (OpenAI) | Transcription voix Wolof |
| **TTS** | `xTTS-v2-wolof` | Coqui xTTS | Synthèse + clonage voix |

---

## Architecture cible

```
🎙️ Agriculteur parle en Wolof
         ↓
whisper-large-v3-wo          ← HF Inference API  (ASR)
         ↓ texte Wolof
wolof-To-French-Translator   ← HF Inference API  (NLLB Wo→Fr)
         ↓ texte Français
┌─────────────────────────────┐
│  Pipeline agronomique       │
│  existant (Andd Baay V1)    │
│  RAG + conseils_agricoles   │
│  + prévision rendement IA   │
│  + BaayVision (maladies)    │
└─────────────────────────────┘
         ↓ réponse Français
wolof-To-French-Translator   ← HF Inference API  (NLLB Fr→Wo)
         ↓ texte Wolof
xTTS-v2-wolof                ← HF Inference API  (TTS)
         ↓
🔊 Agriculteur entend en Wolof
```

**Principe directeur :** la couche de traduction comme pont — toute l'intelligence
agronomique reste en français (RAG, conseils, prédictions). Le Wolof enveloppe
l'interface, pas le moteur. Plus maintenable qu'un RAG natif Wolof.

---

## Fichiers à créer / modifier

### Nouveau — `baay/services/galsenai_service.py`
```python
HF_MODELS = {
    "asr":  "galsenai/whisper-large-v3-wo",
    "trad": "galsenai/wolof-To-French-Translator",
    "tts":  "galsenai/xTTS-v2-wolof",
    "llm":  "galsenai/llama-2-7B_wolof_qa_assistant",
}

def transcribe_wolof(audio_bytes: bytes) -> str          # ASR
def wolof_to_french(text: str) -> str                    # traduction
def french_to_wolof(text: str) -> str                    # traduction inverse
def synthesize_wolof(text: str, voice_sample=None) -> bytes  # TTS (+ clonage)
```

### Modifier — `baay/voice_assistant_service.py`
Les stubs `# simulé` sont déjà localisés avec `locale_hint: "wo"`.
Remplacer par des appels réels à `galsenai_service`.

### Modifier — `andd_baay/settings.py`
```python
GALSENAI_HF_TOKEN  = env("HF_API_TOKEN", default="")
GALSENAI_TTS_VOICE = env("GALSENAI_TTS_VOICE", default="default")  # ou path sample
```

### Modifier — `baay/services/rag_service.py`
Le `# TODO: Traduction question si locale != fr` à la ligne 275 est le hook exact.

---

## Choix d'hébergement (décision à prendre en V2)

| Option | Latence | Coût/mois | Recommandation |
|---|---|---|---|
| HF Inference API serverless | 2–20s (cold start) | ~$0 | PoC / dev uniquement |
| **HF Dedicated Endpoint** | **0.5–2s** | **~$60 (GPU T4)** | **✅ Production** |
| Replicate.com | 1–4s | pay-per-use | Alternative simple |
| HF Spaces (Gradio) | variable | gratuit (quota) | Démo uniquement |

> ⚠️ Seuil UX critique pour l'interaction vocale : **< 3s end-to-end**.
> Le serverless avec cold start peut dépasser 15s — rédhibitoire pour des
> agriculteurs non-lettrés qui ne comprennent pas pourquoi ça "bugue".

---

## Plan d'implémentation V2

### Phase 1 — Traduction + ASR (~2 jours)
- Créer `galsenai_service.py` avec appels HF Inference API
- Brancher STT (whisper-large-v3-wo) dans `voice_assistant_service.py`
- Brancher traduction Wo→Fr et Fr→Wo
- Tests sur questions agricoles types : semis mil, prix arachide, maladie feuilles

### Phase 2 — TTS Wolof (~1 jour)
- Réponses vocales synthétisées via xTTS-v2-wolof
- Sélecteur de langue dans l'UI (fr / wo / ff)
- Option clonage voix à partir d'un sample (agent coopérative locale)

### Phase 3 — LLM Wolof natif (après collecte données)
- Brancher `llama-2-7B_wolof_qa_assistant` comme fallback pour requêtes hors domaine
- Envisager contribution au dataset Waxal avec des transcriptions Andd Baay
- Fine-tuning domaine agricole Sahel si volume suffisant

---

## Références

- HuggingFace GalsenAI : https://huggingface.co/galsenai
- Plateforme Waxal : https://waxal.galsen.ai
- Dataset WaxalNLP : https://huggingface.co/datasets/galsenai/WaxalNLP
- Modèle ASR : https://huggingface.co/galsenai/whisper-large-v3-wo
- Modèle TTS : https://huggingface.co/galsenai/xTTS-v2-wolof
- Traducteur : https://huggingface.co/galsenai/wolof-To-French-Translator
