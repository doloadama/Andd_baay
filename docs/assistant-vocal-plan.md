# Assistant vocal Wolof (Jëf Baay) — Plan & options

> Document de décision. Objectif : choisir comment faire transcrire (ASR) + répondre (LLM)
> en Wolof, vu nos contraintes (produit sahélien, budget serré, déploiement Django sans GPU,
> compte Google probablement UE).

---

## 0. Où on en est (déjà fait, branche `feat/vocal-huggingface`)

- ✅ Pipeline **asynchrone** (Celery + polling) — pas de blocage 3G.
- ✅ **Pivot Gemini** : audio → transcription + réponse Wolof en **1 appel** (`gemini_vocal.py`).
- ✅ **Support Vertex AI** (région US forcée) pour contourner le quota UE — activable par env.
- ✅ Retry auto sur 429, TTS différé, **14 tests** mockés (0 réseau/quota).
- ⛔ **Bloqué** : quota Google à 0 (free-tier ET région `europe-west1`). Rien testé en réel encore.
- 🔭 **Inconnu n°1** : la **qualité de transcription Wolof de Gemini** (pas encore mesurée).

**Constat clé** : les modèles `galsenai/*` ne sont plus servis en serverless HF. Toute voie
« modèle dédié » implique de le **servir nous-mêmes** (GPU) ou de payer un endpoint.

---

## 1. Les 3 briques à décider séparément

L'assistant = **ASR** (audio→texte) + **LLM** (texte→réponse) + **TTS** (réponse→audio, différé).
Chaque brique peut venir d'une source différente. C'est l'axe qui structure toutes les options.

| Brique | Sources possibles |
|---|---|
| ASR (transcription) | Gemini · Whisper-wo fine-tuné (local/GPU) · API tierce |
| LLM (réponse) | Gemini · templates/FAQ Wolof · LLM local (infaisable sur notre infra) |
| TTS (voix) | Différé · Gemini TTS · xTTS-wolof (local) · voix navigateur |

---

## 2. Options de bout en bout

### Option A — Tout Gemini via Vertex AI  ⭐ (voie déjà codée)
ASR + LLM en 1 appel, région US (contourne quota UE).

- **Effort** : ~0 (déjà fait). Reste : config GCP (service account + 3 env vars).
- **Coût** : ~0,0004 $/requête. 10 000 requêtes/mois ≈ **4 $/mois**. Quasi gratuit.
- **Infra** : aucune (pas de GPU, pas de serveur en plus).
- **Qualité** : excellente pour le LLM ; **Wolof ASR à valider** (inconnu n°1).
- **Hors-ligne** : ❌ (appel réseau requis).
- **Risque** : dépendance Google ; qualité Wolof incertaine.

### Option B — Tout Gemini via clé API d'un projet US
Identique à A mais auth par simple clé (pas de service account), si tu crées une clé
depuis un projet Google en région US.

- **Effort** : ~0 (le code clé-API existe déjà). Reste : générer la clé US.
- **Coût / infra / qualité** : idem A.
- **Avantage** : plus simple que Vertex (pas de JSON de service account).
- **Risque** : selon ton compte, le quota peut rester bridé en UE → Vertex est plus sûr.

### Option C — ASR local (Whisper-wo fine-tuné) + Gemini pour la réponse  (hybride)
On entraîne un Whisper sur `galsenai/wolof-audio-data` (28 807 ex.), on le sert nous-mêmes
pour la transcription, et Gemini génère la réponse à partir du texte.

- **Entraînement** : faible difficulté, **une fois**. Kaggle/Colab GPU gratuit, quelques heures.
  Coût ~0 à 30 $. Sortie : modèle Whisper Wolof (~0,5–3 Go selon la taille).
- **Service (le vrai coût, récurrent)** :
  - Whisper-small sur **CPU** : ~la durée réelle (clip 10 s → 10–30 s). Limite mais jouable, gratuit.
  - Whisper-large sur **GPU** : qualité max mais ~10 Go VRAM → VPS GPU (~30–150 $/mois) ou HF Endpoint.
- **Qualité** : ASR Wolof potentiellement **meilleure que Gemini** (modèle dédié).
- **Hors-ligne** : partiel (ASR local possible ; réponse Gemini = réseau).
- **Risque** : on réintroduit l'infra GPU/latence qu'on avait fui. Justifié **seulement si Gemini
  transcrit mal le Wolof**.

### Option D — Tout local (ASR + LLM Wolof)
Whisper-wo + FineLlama-8B servis localement.

- **Verdict** : ❌ **infaisable sur notre stack**. Servir un LLM 8B exige un GPU sérieux 24/7
  (≥16 Go VRAM, ~150–500 $/mois). Hors budget produit sahélien.
- À ne considérer que si un sponsor/GPU dédié apparaît.

### Option E — ASR local + réponses par templates/FAQ Wolof (zéro LLM)
Whisper local transcrit ; la réponse vient d'une base de Q/R agricoles Wolof pré-écrites
(matching par mots-clés / similarité).

- **Effort** : moyen (rédiger la FAQ Wolof + matching). **Indépendance totale** d'une API LLM.
- **Coût** : ASR local uniquement (cf. Option C).
- **Hors-ligne** : ✅ possible entièrement.
- **Qualité réponse** : limitée aux questions prévues, mais **fiable et explicable**.
- **Bon fallback** : sert aussi de « mode démo » quand l'IA est indisponible.

---

## 3. Comparatif synthétique

| Critère | A (Vertex) | B (clé US) | C (ASR local+Gemini) | D (tout local) | E (local+FAQ) |
|---|---|---|---|---|---|
| Effort restant | Config GCP | Générer clé | Élevé | Très élevé | Moyen-élevé |
| Coût mensuel | ~quelques $ | ~quelques $ | CPU 0 / GPU 30-150 $ | 150-500 $ | CPU 0 / GPU |
| Qualité ASR Wolof | ? à tester | ? à tester | ↑ (dédié) | ↑ | ↑ |
| Qualité réponse | ↑↑ | ↑↑ | ↑↑ | ↑ | moyenne |
| Hors-ligne | ❌ | ❌ | partiel | ✅ | ✅ |
| Dépendance Google | forte | forte | moyenne | nulle | nulle |
| Réintroduit du GPU | non | non | oui (si large) | oui | oui (si large) |

---

## 4. Séquencement recommandé (sans s'enfermer)

1. **Débloquer Vertex** (config GCP) → **mesurer la qualité ASR Wolof de Gemini** sur de vrais
   enregistrements. *C'est l'info qui tranche tout.* Effort quasi nul, on a déjà le code.
2. **Si Gemini transcrit bien le Wolof** → **Option A/B**, on s'arrête là. Zéro infra, ~gratuit.
   On ajoute juste un **mode démo/FAQ** (briques de l'Option E) comme filet de sécurité hors-ligne.
3. **Si Gemini est faible en Wolof** → **Option C** : on fine-tune Whisper (notebook prêt à lancer),
   et on choisit le service selon le budget (CPU gratuit lent, ou GPU payant rapide).
   Gemini reste pour la réponse.
4. **Hors-ligne natif exigé un jour** → évoluer vers **Option E** (ASR local + FAQ Wolof).

> Principe : **ne pas entraîner avant l'étape 1**. On ne paie l'entraînement + le service GPU
> que si la mesure prouve que Gemini ne suffit pas. Sinon c'est résoudre un problème inexistant.

---

## 5. Ce que je peux préparer en parallèle (sans bloquer)

- **Notebook de fine-tuning Whisper** (`galsenai/wolof-audio-data`, prêt pour Kaggle/Colab GPU
  gratuit) — écrit mais non lancé, prêt si on bascule en Option C.
- **Mode démo / FAQ Wolof** (briques Option E) — utile quel que soit le choix final
  (fallback hors-ligne + démo sans clé).
- **Tests** — déjà faits (14, mockés).

---

## 6. Questions ouvertes pour ta réflexion de ce soir

1. **Budget GPU** : prêt à payer un petit GPU (~30-150 $/mois) si la qualité l'exige, ou strict zéro-infra ?
2. **Hors-ligne** : est-ce un *must* pour le vocal (zones blanches), ou un *nice-to-have* ?
3. **Exigence de qualité Wolof** : « ça doit comprendre parfaitement » vs « suffisant pour des
   questions agricoles courantes » ?
4. **Indépendance** : la dépendance à Google est-elle un problème stratégique (souveraineté données) ?

Les réponses 1 et 3 déterminent A/B vs C. La réponse 2 fait pencher vers E à terme.
