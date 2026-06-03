# État du projet & décisions (contexte durable)

> Référencé depuis `CLAUDE.md`. À lire pour reprendre le travail sans re-explorer.

## Assistant vocal Wolof « Jëf Baay »

**Contexte décisif** : les modèles `galsenai/*` (whisper-large-v3-wo, FineLlama-3.1-8B,
xTTS-v2-wolof) **ne sont plus servis** sur l'API HuggingFace serverless
(« not deployed by any Inference Provider »). L'ancienne intégration HF est morte.

**Architecture retenue (hybride, services interchangeables)** :
```
Audio → STT → FAQ Wolof locale → LLM (questions ouvertes) → fallback Wolof (jamais muet)
```
- **STT** : `VOCAL_STT_BACKEND` = `gemini` (audio natif, 1 appel) | `whisper_local`
  (microservice `vocal-stt/`, Faster-Whisper `M9and2M/whisper-small-wolof` converti
  CTranslate2, CPU). STT local **validé en réel** (WER bas sur audio Wolof natif).
- **NLU** : `baay/services/wolof_faq.py` — 16 intentions agricoles, déterministe,
  hors-ligne. ⚠️ **contenu Wolof = SEED à faire valider par un locuteur natif**
  (la logique de matching est définitive).
- **LLM** : `VOCAL_LLM_BACKEND` = `gemini` | `ollama` (`vocal-llm/`, FineLlama-Wolof
  GGUF). Services : `baay/services/gemini_vocal.py`, `baay/services/ollama_responder.py`.
- **TTS** : **différé** (xTTS = licence non-commerciale, incompatible tiers payants).
- Pipeline **async** (Celery `process_vocal_task` + polling), retry 429.
  Tâche : `baay/tasks/vocal.py`.

**Blocage prod actuel** : quota Gemini = **0 en région UE** (`europe-west1`).
Débloquer via **Vertex AI région US** (`GEMINI_USE_VERTEX=true` + `GOOGLE_CLOUD_PROJECT`
+ service account) OU clé d'un projet US. Diagnostic : `python manage.py verify_galsenai`.

Plan complet des options : `docs/assistant-vocal-plan.md`.

⚠️ Vérifier que `baay/tasks/vocal.py` importe `gemini_vocal`/`whisper_local`, **pas**
l'ancien `galsenai_service` (un mauvais merge avait fait régresser ce fichier ; corrigé).

## CSS — namespace `--ab-*`

Migration faite sur `main` : tokens canoniques `--ab-*`. Stylelint
(`.stylelintrc.json`) impose le préfixe `^(ab|tw|bs|fa)-` ; gate CI ratchet (lint des
seuls fichiers modifiés). Vendor `--tw-/--bs-/--fa-` tolérés. ~330 tokens sémantiques
legacy (`--danger-`, `--success-`…) restent à remapper (Phase 3, non bloquant).

## Pilier rendement (ML) — verdict & garde-fous

**Deux chemins « rendement chiffré », tous deux non déployables aujourd'hui :**

1. **Nowcast satellite (Zindi CGIAR)** — `ml/kaggle/train_yield_nowcast.py`.
   Cubes Sentinel-2 (360,41,41) = 12 pas × 30 bandes → features tabulaires → XGBoost.
   Après campagne d'optim complète (décodage bandes confirmé, centre 9×9 anti
   pixel-mixte, climat TerraClimate, masquage nuages QA60, indices red-edge
   NDRE/GNDVI/NDWI, interpolation des trous nuageux, régularisation, baseline CV
   honnête) : **plafond R²≈0.05 inter-année (GroupKFold), ≈0.21 intra-saison**.
   → **Inutilisable comme chiffre** (RMSE 1.7 t/ha pour moy 3.2 = ±53 %).
   `Quality==3` (44 % du dataset) = bruit. **Verdict : signal réel mais trop faible.**
   Piste résiduelle : NDVI/NDRE en **indicateur RELATIF** (vs médiane locale),
   label-free, déployable — pas un prédicteur chiffré.

2. **Modèle pré-campagne par culture** — `baay/services/ml_training.py`.
   ⚠️ **Les seules données labellisées actuelles (121 obs) sont SYNTHÉTIQUES**
   (générées par `seed_projets_fictifs`). Entraîner dessus = réapprendre le
   générateur (R² artificiellement parfait → prédiction factice).

**Garde-fous d'intégrité en place :**
- `PrevisionFeatures.synthetique` (BooleanField indexé). Migration `0057` a
  rétro-marqué les 121 obs seed (projets `[TEST]` / Ferme Test ML).
- `seed_projets_fictifs` pose `synthetique=True` sur tout ce qu'il crée.
- `ml_training.entrainer_culture` + `cultures_a_reentrainer` **excluent le
  synthétique par défaut** (override `inclure_synthetique=True`).
- Vérifié : 121 labels = 121 synthétiques = 0 réel → `cultures_a_reentrainer() == []`
  → **aucun modèle entraîné**, repli moteur à règles (`estimer_rendement_ia`,
  confiance base 50 « système à règles non validé »). Les seuils `MIN_TRAIN_OBS=30`
  / `MIN_R2=0.30` prendront le relais quand du **vrai `rendement_reel`** s'accumulera.

**Vrai déblocage = instrumenter la capture de rendement réel terrain** (pesées /
déclarations à la clôture des projets). C'est la seule voie vers un modèle légitime.

## Branches actives (toutes poussées sauf indication)

| Branche | Objet | Statut |
|---|---|---|
| `hotfix/redis-broker-auth` | fix auth Redis Railway (URL broker) | à merger |
| `feat/vocal-stt-local` | assistant vocal hybride complet (29 tests) | PR à ouvrir |
| `feat/landing-deploy` | nouvelle landing `home.html` (`.ab-land`) | PR à ouvrir |
| `refactor/vocal-async-css-namespace` | async vocal + migration CSS | mergé dans main |
| `feat/ml-hardening` | anti-fuite ML + nowcast Kaggle (verdict) + garde-fou anti-synthétique (migr. 0056/0057) | PR à ouvrir |
