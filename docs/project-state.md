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

## SEO — package indexabilité + contenu (branche `feat/seo-quickwins`)

Contexte : avant, **rien d'indexable** (tout derrière login) → Google n'avait rien à classer.
Audit complet fait (on-page + technique, ancré sur les templates réels).

**Livré (5 commits, branche poussée, PR à ouvrir) :**
1. **Fondation** : `robots.txt` (vue `baay/views.py:robots_txt`), `sitemap.xml`
   (`django.contrib.sitemaps` + `baay/sitemaps.py`), `<link canonical>` (`request.path`,
   donc dédupe `?source/?page`), JSON-LD Organization/WebSite + OG/Twitter dans `base.html`,
   HSTS 1 an.
2. **Pilier #1 Actualités** publiques `/actualites/` + hubs `/actualites/<categorie>/`
   (`views_actualites.py` dé-authentifié ; anti-duplicate : `resume` only, lien `url_originale`).
3. **Pilier #2 Calendrier cultural** `/calendrier-cultural/` + `/<slug>/`
   (dataset curé `baay/calendrier_cultural.py`, 8 cultures ; frise de semis ; FAQPage JSON-LD).
   ⚠️ statique car `ProduitAgricole` a des champs agronomiques NULL sur les cultures clés.
4. **Pilier #3 Prix du marché** `/prix-marche/` + `/<slug>/` **data-driven**
   (`views_marche.py` : `prix_public_liste/detail` ; **zéro page vide** — 404/noindex si pas de
   données ; `Product`+`AggregateOffer` JSON-LD ; sitemap dynamique). `PrixMarche` vide en local.
5. **Carte sociale** `og:image` 1200×630 (`baay/static/images/og-card.png`, généré par
   `scripts/generate_og_card.py`).

Sitemaps enregistrés dans `baay/sitemaps.py` : `static`, `actualites`, `calendrier`, `prix`.
Liens publics ajoutés au footer de `base.html` (Actualités, Calendrier, Prix). Tests :
`tests/test_seo.py`, `test_actualites_public.py`, `test_calendrier.py`, `test_prix_public.py`.

**⚠️ À FAIRE EN PROD après merge** (sinon sitemap avec mauvais host) :
```python
from django.contrib.sites.models import Site
Site.objects.update_or_create(id=1, defaults={
    "domain": "andd-baay-production.up.railway.app", "name": "Andd Baay"})
```
Puis soumettre `/sitemap.xml` à Google Search Console.

## Branches actives (toutes poussées sauf indication)

| Branche | Objet | Statut |
|---|---|---|
| `hotfix/redis-broker-auth` | fix auth Redis Railway (URL broker) | à merger |
| `feat/vocal-stt-local` | assistant vocal hybride complet (29 tests) | PR à ouvrir |
| `feat/landing-deploy` | nouvelle landing `home.html` (`.ab-land`) | PR à ouvrir |
| `refactor/vocal-async-css-namespace` | async vocal + migration CSS | mergé dans main |
| `feat/ml-hardening` | anti-fuite ML + nowcast Kaggle (verdict) + garde-fou anti-synthétique + capture rendement réel | PR à ouvrir |
| `feat/seo-quickwins` | package SEO complet (fondation + 3 piliers contenu + og:image) | PR à ouvrir |
