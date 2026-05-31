"""
Assistant vocal agricole Wolof — pipeline modulaire (Strategy pattern).

Architecture (cf. docs/v2-wolof-vocal-galsenai.md) :

    🎙️ audio Wolof
        → STT            (VOCAL_STT_BACKEND)
        → Détection d'incident locale (déterministe, AVANT tout LLM)
            ├─ incident majeur ? → enregistrement + accusé vocal rapide (pas de LLM)
            └─ sinon ↓
        → Pont NLLB Wo→Fr  (si locale="wo")
        → LLM agronomique en Français  (VOCAL_LLM_BACKEND)
        → Pont NLLB Fr→Wo
        → TTS Wolof        (VOCAL_TTS_BACKEND)
        → 🔊 réponse

Backends interchangeables via variables d'environnement :
    VOCAL_STT_BACKEND : simulated | whisper-galsenai | local-whisper
    VOCAL_LLM_BACKEND : simulated | gemini | ollama
    VOCAL_TTS_BACKEND : simulated | xtts-galsenai

Principe directeur : l'intelligence agronomique reste en français ; le Wolof
enveloppe l'interface (traduction comme pont). La détection d'incident est
locale, déterministe, gratuite et court-circuite le LLM.

Conçu pour Celery : étapes non bloquantes `stt_stage` / `respond_stage` /
`tts_stage`, orchestrées par `process_vocal_audio` (audio brut → résultat).
Le contrat de `run_vocal_query_pipeline` (texte → payload) est préservé pour la vue.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTES MÉTIER
# ============================================================================

SYSTEM_DIRECTIVE_SAHEL = (
    "Tu es un conseiller agricole expert pour les zones sahéliennes (Sénégal). "
    "Tes réponses doivent être concises, pratiques et respectueuses des traditions locales. "
    "Réponds en français de façon claire et actionnable."
)

AGRIC_HINTS_SNIPPETS = (
    "Rotation céréales-légumineuses pour préserver la structure du sol sahélien.",
    "Irrigation goutte-à-goutte : mieux vaut plusieurs apports courts qu'un lessivage unique.",
    "Semis après les premières pluies (≥20–30 mm cumulés) pour limiter le stress hydrique initial.",
    "Engrais : privilégier l'apport local (compost, fumier bien décomposé) avant la montée des prix des intrants.",
    "Pulaar / Wolof : utiliser un ton direct, respect des aînés dans les formulations conseillées.",
)

# ============================================================================
# DÉTECTION D'INCIDENTS AGRICOLES (déterministe, hands-free) — INCHANGÉE
# ============================================================================

AGRIC_INCIDENT_PATTERNS: dict[str, dict[str, Any]] = {
    'invasion_ravageurs': {
        'keywords': [
            'criquet', 'criquets', 'sauterelle', 'chenille', 'chenilles',
            'invasion', 'ravageur', 'ravageurs', 'locuste', 'acridien',
            'larves', 'insectes', 'pucerons', 'cochenilles',
        ],
        'default_gravite': 'haute',
        'keywords_grave': ['invasion', 'massive', 'dévastation', 'tout mangé', 'dégâts importants'],
    },
    'maladie_feuilles': {
        'keywords': [
            'maladie', 'taches', 'feuilles', 'jaunissement', 'pourriture',
            'oïdium', 'rouille', 'mildiou', 'brûlure', 'décoloration',
            'feuilles mortes', 'chute des feuilles',
        ],
        'default_gravite': 'moyenne',
        'keywords_grave': ['pourriture', 'mort', 'sèche', 'toutes les feuilles'],
    },
    'maladie_racines': {
        'keywords': [
            'racines', 'tige', 'flétri', 'fané', 'pourriture racines',
            'couronne', 'collet', 'charançon', 'ver', 'ver blanc',
            'nematode', 'aflatoxine',
        ],
        'default_gravite': 'haute',
        'keywords_grave': ['pourriture', 'mort subite', 'faner', 'flétri complet'],
    },
    'stress_hydrique': {
        'keywords': [
            'sècheresse', "pas d'eau", 'manque eau', 'stress hydrique',
            'sol sec', 'terre craquelée', 'pas pluie', 'irrigation en panne',
            'canal cassé',
        ],
        'default_gravite': 'moyenne',
        'keywords_grave': ['critique', 'urgence eau', 'plantes mortes', 'sècheresse sévère'],
    },
    'inondation': {
        'keywords': [
            'inondation', "trop d'eau", 'eau stagnante', 'champ inondé',
            'ruissellement', 'pluies torrentielles', 'déluge', 'cyclone',
            'dégâts eau',
        ],
        'default_gravite': 'haute',
        'keywords_grave': ['inondation totale', 'submergé', 'tout emporté', 'dégâts majeurs'],
    },
    'vol': {
        'keywords': [
            'vol', 'volé', 'intrusion', 'voleur', 'animaux errants',
            'bétail', 'moutons', 'chèvres', 'bœufs', 'dégâts animaux',
            'braconnage', 'pillé',
        ],
        'default_gravite': 'moyenne',
        'keywords_grave': ['gros vol', 'tout volé', 'intrusion armée', 'menaces'],
    },
    'incident_materiel': {
        'keywords': [
            'panne', 'moto-pompe', 'tracteur', 'outil cassé', 'matériel',
            'tuyau percé', 'réservoir fuit', 'clôture endommagée',
            'serre détruite', 'forage en panne',
        ],
        'default_gravite': 'faible',
        'keywords_grave': ['incendie', 'accident', 'blessé', 'détruit totalement'],
    },
}

URGENCY_MARKERS = [
    'urgent', 'urgence', 'vite', 'rapidement', 'immédiat', 'maintenant',
    'aide', "à l'aide", 'danger', 'critique', 'sauvez', 'catastrophe',
]

LOCALISATION_PATTERNS = [
    r'(?:parcelle|champ|zone|secteur|bloc|zone)\s+([A-Za-z\s\-]+?)(?:\s+(?:\d+|au|dans|sur|vers|,|\.))',
    r'(?:nord|sud|est|ouest|nord-est|nord-ouest|sud-est|sud-ouest)(?:\s+(?:du champ|de la parcelle|de la ferme))?',
    r'(?:près de|à côté de|contre|au niveau de)\s+([A-Za-z\s\-]+?)(?:\s+(?:\d+|,|\.))',
]


def _normalize_text(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "").strip().lower()
    return re.sub(r"\s+", " ", t)


def _detecter_type_incident(text_normalized: str) -> tuple[str | None, str, float]:
    """Analyse le texte (normalisé) → (type_incident, gravite, confidence)."""
    if not text_normalized:
        return None, 'moyenne', 0.0

    best_match = None
    best_score = 0.0

    for incident_type, config in AGRIC_INCIDENT_PATTERNS.items():
        score = 0.0
        for kw in config['keywords']:
            if kw in text_normalized:
                score += 1
        for urgency in URGENCY_MARKERS:
            if urgency in text_normalized:
                score += 0.5
        if score > best_score:
            best_score = score
            best_match = (incident_type, config)

    if best_score < 1 or best_match is None:
        return None, 'moyenne', 0.0

    incident_type, config = best_match
    gravite = config['default_gravite']
    for grave_kw in config['keywords_grave']:
        if grave_kw in text_normalized:
            gravite = {'faible': 'moyenne', 'moyenne': 'haute', 'haute': 'critique'}.get(gravite, gravite)
            break
    for urgency in URGENCY_MARKERS:
        if urgency in text_normalized and gravite != 'critique':
            gravite = {'faible': 'moyenne', 'moyenne': 'haute'}.get(gravite, gravite)
            break

    confidence = min(0.95, 0.3 + best_score * 0.15)
    return incident_type, gravite, confidence


def _extraire_parcelle(text_normalized: str) -> str:
    """Tente d'extraire le nom de parcelle/zone du texte."""
    for pattern in LOCALISATION_PATTERNS:
        match = re.search(pattern, text_normalized, re.IGNORECASE)
        if match:
            return match.group(1).strip() if match.groups() else match.group(0).strip()
    simple = re.search(r'(?:parcelle|champ|zone|secteur)\s*([A-Z0-9]+)', text_normalized, re.IGNORECASE)
    return simple.group(0).strip() if simple else ''


def enregistrer_incident_vocal(
    *,
    ferme_id: str,
    profile_id: str,
    transcript_text: str,
    audio_url: str | None = None,
    gps_lat: float | None = None,
    gps_lon: float | None = None,
    locale_hint: str = "fr",
) -> dict[str, Any]:
    """Enregistre un incident agricole signalé par voix (si détecté)."""
    from baay.models import IncidentRapporte, Ferme, Profile

    text_normalized = _normalize_text(transcript_text)
    incident_type, gravite, confidence = _detecter_type_incident(text_normalized)

    if not incident_type:
        logger.info("Aucun incident agricole détecté dans: %s", transcript_text[:100])
        return {
            "incident_detecte": False,
            "message": "Aucun incident agricole identifié dans le message vocal.",
            "transcript": transcript_text,
        }

    parcelle = _extraire_parcelle(transcript_text)
    try:
        ferme = Ferme.objects.get(pk=ferme_id)
        profile = Profile.objects.get(pk=profile_id)
        incident = IncidentRapporte.objects.create(
            ferme=ferme,
            signale_par=profile,
            type_incident=incident_type,
            gravite_detectee=gravite,
            statut='signale',
            transcription_audio=transcript_text,
            audio_url=audio_url,
            localisation_gps_lat=gps_lat,
            localisation_gps_lon=gps_lon,
            parcelle_concernee=parcelle,
        )
        logger.info(
            "Incident vocal créé: type=%s gravite=%s ferme=%s parcelle=%s",
            incident_type, gravite, ferme.nom, parcelle or "non précisée",
        )
        return {
            "incident_detecte": True,
            "incident_id": str(incident.id),
            "type_incident": incident_type,
            "type_incident_display": incident.get_type_incident_display(),
            "gravite": gravite,
            "gravite_display": incident.get_gravite_detectee_display(),
            "parcelle": parcelle,
            "ferme": ferme.nom,
            "message": f"Incident signalé: {incident.get_type_incident_display()} - {incident.get_gravite_detectee_display()}",
            "transcript": transcript_text,
            "confidence_detection": round(confidence, 2),
        }
    except Ferme.DoesNotExist:
        logger.error("Ferme introuvable: %s", ferme_id)
        return {"incident_detecte": False, "error": "ferme_introuvable"}
    except Profile.DoesNotExist:
        logger.error("Profile introuvable: %s", profile_id)
        return {"incident_detecte": False, "error": "profile_introuvable"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erreur création incident vocal")
        return {"incident_detecte": False, "error": str(exc)}


# ============================================================================
# RÉPONSE SIMULÉE (RAG léger) — fallback déterministe sans réseau
# ============================================================================

def _rag_simulated_snippets(query: str, max_snippets: int = 2) -> list[str]:
    q = _normalize_text(query)
    if not q:
        return []
    scored = []
    for snip in AGRIC_HINTS_SNIPPETS:
        base = _normalize_text(snip)
        score = sum(1 for w in q.split() if len(w) > 3 and w in base)
        scored.append((score, snip))
    scored.sort(key=lambda x: -x[0])
    picked = [s for sc, s in scored if sc > 0][:max_snippets]
    return picked or ([scored[0][1]] if scored else list(AGRIC_HINTS_SNIPPETS[:1]))


def _draft_answer(user_text: str, snippets: list[str], locale_hint: str) -> str:
    """Réponse déterministe « expert terrain » (mode simulated / fallback)."""
    loc = (locale_hint or "fr")[:2].lower()
    opener = {
        "wo": "Ci sahel bi, am nañu waxtaan bu ñuy jëfandikoo léegi ci sa laaj.",
        "ff": "E nder rewɓe ɓe sahël, ena faalande woni heennoonde.",
    }.get(loc, "Voici une piste concrète pour votre situation au Sahel.")
    lines = [opener, "", "Conseils :"]
    for i, sn in enumerate(snippets, 1):
        lines.append(f"  {i}. {sn}")
    lines += [
        "",
        "À faire sur le terrain : vérifier l'humidité des 10 premiers cm, l'état "
        "racinaire, et ajuster l'irrigation ou le semis selon les pluies des 7 derniers jours.",
    ]
    return "\n".join(lines)


# ============================================================================
# CONFIG DES BACKENDS (Strategy pattern via env)
# ============================================================================

STTBackend = Literal["simulated", "whisper-galsenai", "local-whisper"]
LLMBackend = Literal["simulated", "gemini", "ollama"]
TTSBackend = Literal["simulated", "xtts-galsenai"]


def _stt_backend() -> str:
    return getattr(settings, "VOCAL_STT_BACKEND", "simulated").strip().lower()


def _llm_backend() -> str:
    # Réutilise VOCAL_LLM_BACKEND ; "deepseek" est aussi accepté (cf. deepseek_responder).
    return getattr(settings, "VOCAL_LLM_BACKEND", "simulated").strip().lower()


def _tts_backend() -> str:
    return getattr(settings, "VOCAL_TTS_BACKEND", "simulated").strip().lower()


def _translation_bridge_enabled() -> bool:
    """Le pont NLLB n'a de sens que pour le Wolof et si activé."""
    return getattr(settings, "VOCAL_TRANSLATION_BRIDGE", True)


# ============================================================================
# ÉTAPE 1 — STT (dispatch)
# ============================================================================

def transcribe(audio_bytes: bytes, *, mime_type: str = "audio/webm", locale_hint: str = "wo") -> str:
    """
    Transcrit l'audio selon VOCAL_STT_BACKEND. Lève RuntimeError si le backend
    échoue (l'orchestrateur décide du repli / message d'erreur).
    """
    backend = _stt_backend()
    if backend == "local-whisper":
        from baay.services.whisper_local import transcribe_audio
        return transcribe_audio(audio_bytes, mime_type=mime_type)
    if backend == "whisper-galsenai":
        from baay.services.galsenai_service import transcribe_wolof
        return transcribe_wolof(audio_bytes, mime_type=mime_type)
    # simulated : pas de vrai décodage audio (dev / tests sans modèle).
    logger.info("STT simulé (aucun backend réel configuré).")
    return getattr(settings, "VOCAL_SIMULATED_TRANSCRIPT", "(transcription simulée)")


# ============================================================================
# PONT DE TRADUCTION (NLLB Wolof ↔ Français)
# ============================================================================

def _to_french(text: str, locale_hint: str) -> tuple[str, bool]:
    """Traduit vers le français si locale=wo et pont actif. Retourne (texte_fr, traduit?)."""
    if locale_hint[:2].lower() == "wo" and _translation_bridge_enabled():
        try:
            from baay.services.galsenai_service import wolof_to_french
            return wolof_to_french(text), True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pont Wo→Fr indisponible (%s) — on garde le texte source.", exc)
    return text, False


def _to_wolof(text: str, *, did_translate: bool) -> str:
    """Re-traduit la réponse FR→Wo si on avait traduit à l'aller."""
    if did_translate:
        try:
            from baay.services.galsenai_service import french_to_wolof
            return french_to_wolof(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pont Fr→Wo indisponible (%s) — réponse renvoyée en français.", exc)
    return text


# ============================================================================
# ÉTAPE 2 — LLM agronomique (dispatch, en français)
# ============================================================================

def _llm_answer_fr(question_fr: str) -> str:
    """
    Interroge le LLM agronomique EN FRANÇAIS selon VOCAL_LLM_BACKEND.
    Repli automatique sur la réponse simulée si le backend échoue (réseau/503/quota).
    """
    backend = _llm_backend()
    try:
        if backend == "gemini":
            from baay.services.gemini_vocal import generate_text
            return generate_text(question_fr, system_text=SYSTEM_DIRECTIVE_SAHEL)
        if backend == "ollama":
            from baay.services.ollama_responder import generate_response
            return generate_response(question_fr, system=SYSTEM_DIRECTIVE_SAHEL)
        if backend == "deepseek":
            from baay.services.deepseek_responder import generate_response
            return generate_response(question_fr)
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM '%s' indisponible (%s) — repli sur réponse simulée.", backend, exc)
    # simulated ou repli
    return _draft_answer(question_fr, _rag_simulated_snippets(question_fr), "fr")


# ============================================================================
# ÉTAPE 3 — TTS (dispatch)
# ============================================================================

def synthesize(text: str, *, locale_hint: str = "wo") -> bytes | None:
    """Synthèse vocale selon VOCAL_TTS_BACKEND. Retourne des octets audio ou None."""
    backend = _tts_backend()
    if backend == "xtts-galsenai":
        try:
            from baay.services.galsenai_service import synthesize_wolof
            return synthesize_wolof(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("TTS xtts-galsenai indisponible (%s).", exc)
            return None
    return None  # simulated : pas d'audio, l'UI lit le texte.


# ============================================================================
# RÉSULTAT TYPÉ
# ============================================================================

@dataclass
class VocalResult:
    """Résultat d'une requête vocale, sérialisable pour le polling HTMX."""
    answer_text: str
    locale: str
    pipeline: list[dict[str, Any]] = field(default_factory=list)
    incident: Optional[dict[str, Any]] = None
    transcript: str = ""
    audio_b64: Optional[str] = None
    tts_available: bool = False
    disclaimer: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer_text": self.answer_text,
            "locale": self.locale,
            "pipeline": self.pipeline,
            "incident": self.incident,
            "transcript": self.transcript,
            "audio_b64": self.audio_b64,
            "tts_available": self.tts_available,
            "disclaimer": self.disclaimer,
        }


# ============================================================================
# HOOKS CELERY — étapes non bloquantes
# ============================================================================

def stt_stage(audio_bytes: bytes, *, mime_type: str = "audio/webm", locale_hint: str = "wo") -> str:
    """[Celery étape 1] Audio brut → transcription. Isolée pour parallélisation."""
    return transcribe(audio_bytes, mime_type=mime_type, locale_hint=locale_hint)


def respond_stage(
    *,
    transcript_text: str,
    locale_hint: str = "wo",
    ferme_id: str | None = None,
    profile_id: str | None = None,
    gps_lat: float | None = None,
    gps_lon: float | None = None,
    audio_url: str | None = None,
) -> VocalResult:
    """
    [Celery étape 2] Transcription → réponse.

    Incident-first : détection locale déterministe AVANT tout LLM. Si incident
    majeur détecté (+ contexte ferme), enregistrement + accusé rapide, sans LLM.
    Sinon : pont Wo→Fr → LLM français → pont Fr→Wo.
    """
    pipeline: list[dict[str, Any]] = [
        {"step": "stt", "backend": _stt_backend()},
    ]
    text_normalized = _normalize_text(transcript_text)
    incident_type, gravite, confidence = _detecter_type_incident(text_normalized)

    # ── Incident-first : court-circuite le LLM ───────────────────────────────
    if incident_type and ferme_id and profile_id:
        incident_result = enregistrer_incident_vocal(
            ferme_id=ferme_id, profile_id=profile_id, transcript_text=transcript_text,
            audio_url=audio_url, gps_lat=gps_lat, gps_lon=gps_lon, locale_hint=locale_hint,
        )
        if incident_result.get("incident_detecte"):
            # Accusé pré-formaté (rapide, sans LLM génératif coûteux).
            ack_fr = (
                f"Incident enregistré : {incident_result['type_incident_display']} "
                f"({incident_result['gravite_display']}). Votre signalement est transmis "
                f"au responsable de la ferme ; un suivi sera fait rapidement."
            )
            ack = _to_wolof(ack_fr, did_translate=(locale_hint[:2].lower() == "wo"
                                                   and _translation_bridge_enabled()))
            pipeline += [
                {"step": "incident_detection", "status": "detected",
                 "type": incident_type, "gravite": gravite, "confidence": round(confidence, 2)},
                {"step": "incident_save", "status": "saved",
                 "incident_id": incident_result.get("incident_id")},
                {"step": "llm", "status": "skipped_incident_ack"},
            ]
            return VocalResult(
                answer_text=ack, locale=locale_hint, pipeline=pipeline,
                incident=incident_result, transcript=transcript_text,
                disclaimer="Incident transmis aux responsables de la ferme.",
            )

    # ── Voie normale : pont de traduction + LLM ──────────────────────────────
    question_fr, did_translate = _to_french(transcript_text, locale_hint)
    pipeline.append({"step": "translate_in", "wo2fr": did_translate})

    answer_fr = _llm_answer_fr(question_fr)
    pipeline.append({"step": "llm", "backend": _llm_backend()})

    answer = _to_wolof(answer_fr, did_translate=did_translate)
    pipeline.append({"step": "translate_out", "fr2wo": did_translate})

    result = VocalResult(
        answer_text=answer, locale=locale_hint, pipeline=pipeline,
        transcript=transcript_text,
        disclaimer="Conseil indicatif ; vérifier les conditions locales avant action.",
    )
    if incident_type and not (ferme_id and profile_id):
        result.incident = {
            "incident_detecte": False, "type": incident_type, "gravite": gravite,
            "reason": "Contexte ferme/utilisateur manquant — non enregistré.",
        }
        pipeline.append({"step": "incident_detection", "status": "detected_not_saved", "type": incident_type})
    return result


def tts_stage(text: str, *, locale_hint: str = "wo") -> bytes | None:
    """[Celery étape 3] Texte → audio (octets) ou None si TTS désactivé/indisponible."""
    return synthesize(text, locale_hint=locale_hint)


def process_vocal_audio(
    audio_bytes: bytes,
    *,
    mime_type: str = "audio/webm",
    locale_hint: str = "wo",
    ferme_id: str | None = None,
    profile_id: str | None = None,
    gps_lat: float | None = None,
    gps_lon: float | None = None,
    with_tts: bool = False,
) -> VocalResult:
    """
    Orchestrateur de bout en bout (audio → résultat), pensé pour une tâche Celery.
    Les 3 étapes (`stt_stage`, `respond_stage`, `tts_stage`) restent appelables
    séparément pour un découpage plus fin si besoin.
    """
    transcript = stt_stage(audio_bytes, mime_type=mime_type, locale_hint=locale_hint)
    result = respond_stage(
        transcript_text=transcript, locale_hint=locale_hint,
        ferme_id=ferme_id, profile_id=profile_id, gps_lat=gps_lat, gps_lon=gps_lon,
    )
    if with_tts and _tts_backend() != "simulated":
        audio = tts_stage(result.answer_text, locale_hint=locale_hint)
        if audio:
            import base64
            result.audio_b64 = base64.b64encode(audio).decode()
            result.tts_available = True
    return result


# ============================================================================
# COMPATIBILITÉ — contrat historique utilisé par baay/views.py
# ============================================================================

def run_vocal_query_pipeline(
    *,
    transcript_text: str,
    locale_hint: str = "fr",
    simulated_stt_confidence: float = 0.92,
    ferme_id: str | None = None,
    profile_id: str | None = None,
    gps_lat: float | None = None,
    gps_lon: float | None = None,
) -> dict[str, Any]:
    """
    Pipeline texte → payload JSON (contrat préservé pour la vue existante).
    Délègue à `respond_stage` (incident-first + pont + LLM modulaire).
    """
    result = respond_stage(
        transcript_text=transcript_text, locale_hint=locale_hint,
        ferme_id=ferme_id, profile_id=profile_id, gps_lat=gps_lat, gps_lon=gps_lon,
    )
    payload = result.to_dict()
    payload["transcript_normalized"] = _normalize_text(transcript_text)
    payload["system_directive_preview"] = SYSTEM_DIRECTIVE_SAHEL[:120] + "…"
    logger.info("vocal_query_pipeline locale=%s incident=%s llm=%s",
                locale_hint, bool(result.incident and result.incident.get("incident_detecte")),
                _llm_backend())
    return payload
