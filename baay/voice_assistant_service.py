"""
Assistant vocal agricole (pipeline simulée : Wolof/Pulaar STT → RAG → TTS).

L’intégration réelle (Whisper dialectal, embeddings locaux, synthèse vocale)
pourra brancher ces points d’extension sans changer le contrat JSON de l’API.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_DIRECTIVE_SAHEL = (
    "Tu es un conseiller agricole expert pour les zones sahéliennes. "
    "Tes réponses doivent être concises, pratiques et respectueuses des traditions locales."
)

# Corpus minimal « expertise » injecté comme RAG simulé (à remplacer par une base vectorielle).
AGRIC_HINTS_SNIPPETS = (
    "Rotation céréales-légumineuses pour préserver la structure du sol sahélien.",
    "Irrigation goutte-à-goutte : mieux vaut plusieurs apports courts que un lessivage unique.",
    "Semis après les premières pluies (≥20–30 mm cumulés) pour limiter le stress hydrique initial.",
    "Engrais : privilégier l’apport local (compost, fumier bien décomposé) avant la montée des prix des intrants.",
    "Pulaar / Wolof : utiliser un ton direct, « ndekki » / respect des aînés dans les formulations conseillées.",
)


# ============================================================================
# DÉTECTION D'INCIDENTS AGRICOLES (Hands-Free Voice Reporting)
# ============================================================================

# Patterns de détection d'incidents avec mots-clés et pondération gravité
AGRIC_INCIDENT_PATTERNS = {
    'invasion_ravageurs': {
        'keywords': [
            'criquet', 'criquets', 'sauterelle', 'chenille', 'chenilles',
            'invasion', 'ravageur', 'ravageurs', 'locuste', 'acridien',
            'larves', 'insectes', 'pucerons', 'cochenilles'
        ],
        'default_gravite': 'haute',
        'keywords_grave': ['invasion', 'massive', 'dévastation', 'tout mangé', 'dégâts importants'],
    },
    'maladie_feuilles': {
        'keywords': [
            'maladie', 'taches', 'feuilles', 'jaunissement', 'pourriture',
            'oïdium', 'rouille', 'mildiou', 'brûlure', 'décoloration',
            'feuilles mortes', 'chute des feuilles'
        ],
        'default_gravite': 'moyenne',
        'keywords_grave': ['pourriture', 'mort', 'sèche', 'toutes les feuilles'],
    },
    'maladie_racines': {
        'keywords': [
            'racines', 'tige', 'flétri', 'fané', 'pourriture racines',
            'couronne', 'collet', 'charançon', 'ver', 'ver blanc',
            'nematode', 'aflatoxine'
        ],
        'default_gravite': 'haute',
        'keywords_grave': ['pourriture', 'mort subite', 'faner', 'flétri complet'],
    },
    'stress_hydrique': {
        'keywords': [
            'sècheresse', 'pas d\'eau', 'manque eau', 'stress hydrique',
            'sol sec', 'terre craquelée', 'pas pluie', 'irrigation en panne',
            'canal cassé'
        ],
        'default_gravite': 'moyenne',
        'keywords_grave': ['critique', 'urgence eau', 'plantes mortes', 'sècheresse sévère'],
    },
    'inondation': {
        'keywords': [
            'inondation', 'trop d\'eau', 'eau stagnante', 'champ inondé',
            'ruissellement', 'pluies torrentielles', 'déluge', 'cyclone',
            'dégâts eau'
        ],
        'default_gravite': 'haute',
        'keywords_grave': ['inondation totale', 'submergé', 'tout emporté', 'dégâts majeurs'],
    },
    'vol': {
        'keywords': [
            'vol', 'volé', 'intrusion', 'voleur', 'animaux errants',
            'bétail', 'moutons', 'chèvres', 'bœufs', 'dégâts animaux',
            'braconnage', 'pillé'
        ],
        'default_gravite': 'moyenne',
        'keywords_grave': ['gros vol', 'tout volé', 'intrusion armée', 'menaces'],
    },
    'incident_materiel': {
        'keywords': [
            'panne', 'moto-pompe', 'tracteur', 'outil cassé', 'matériel',
            'tuyau percé', 'réservoir fuit', 'clôture endommagée',
            'serre détruite', 'forage en panne'
        ],
        'default_gravite': 'faible',
        'keywords_grave': ['incendie', 'accident', 'blessé', 'détruit totalement'],
    },
}

# Mots d'urgence qui augmentent la gravité
URGENCY_MARKERS = [
    'urgent', 'urgence', 'vite', 'rapidement', 'immédiat', 'maintenant',
    'aide', 'à l\'aide', 'danger', 'critique', 'sauvez', 'catastrophe'
]

# Patterns pour extraire localisation
LOCALISATION_PATTERNS = [
    r'(?:parcelle|champ|zone|secteur|bloc|zone)\s+([A-Za-z\s\-]+?)(?:\s+(?:\d+|au|dans|sur|vers|,|\.))',
    r'(?:nord|sud|est|ouest|nord-est|nord-ouest|sud-est|sud-ouest)(?:\s+(?:du champ|de la parcelle|de la ferme))?',
    r'(?:près de|à côté de|contre|au niveau de)\s+([A-Za-z\s\-]+?)(?:\s+(?:\d+|,|\.))',
]


def _normalize_text(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "").strip().lower()
    return re.sub(r"\s+", " ", t)


def _rag_simulated_snippets(query: str, max_snippets: int = 2) -> list[str]:
    q = _normalize_text(query)
    if not q:
        return []
    scored: list[tuple[int, str]] = []
    for snip in AGRIC_HINTS_SNIPPETS:
        base = _normalize_text(snip)
        score = sum(1 for w in q.split() if len(w) > 3 and w in base)
        scored.append((score, snip))
    scored.sort(key=lambda x: -x[0])
    picked = [s for sc, s in scored if sc > 0][:max_snippets]
    if picked:
        return picked
    return [scored[0][1]] if scored else [AGRIC_HINTS_SNIPPETS[0]]


def _draft_answer(user_text: str, snippets: list[str], locale_hint: str) -> str:
    """Réponse déterministe type « expert terrain » (en attendant LLM + TTS)."""
    loc = (locale_hint or "fr")[:2].lower()
    opener = {
        "wo": "Ci sahel bi, am nañu waxtaan bu ñuy jëfandikoo léegi ci sa question.",
        "ff": "E nder rewɓe ɓe sahël, ena faalande woni heennoonde e no mbadii wartirde.",
    }.get(loc, "Voici une piste concrète pour votre situation au Sahel.")

    lines = [
        SYSTEM_DIRECTIVE_SAHEL,
        "",
        opener,
        "",
        "Synthèse (RAG léger — à brancher sur une base métier réelle) :",
    ]
    for i, sn in enumerate(snippets, 1):
        lines.append(f"  {i}. {sn}")
    lines.extend(
        [
            "",
            f"Votre question (transcription simulée) : « {user_text.strip()[:280]} »",
            "",
            "À faire sur le terrain : vérifier l’humidité des 10 premiers cm, l’état racinaire, "
            "et ajuster l’irrigation ou le semis retardé selon les pluies locales des 7 derniers jours.",
        ]
    )
    return "\n".join(lines)


def _detecter_type_incident(text_normalized: str) -> tuple[str | None, str, float]:
    """
    Analyse le texte pour détecter un type d'incident agricole.

    Returns:
        (type_incident, gravite, confidence_score)
    """
    if not text_normalized:
        return None, 'moyenne', 0.0

    best_match = None
    best_score = 0
    detected_type = None

    for incident_type, config in AGRIC_INCIDENT_PATTERNS.items():
        score = 0
        keywords_matched = []

        for kw in config['keywords']:
            if kw in text_normalized:
                score += 1
                keywords_matched.append(kw)

        # Bonus pour mots d'urgence
        for urgency in URGENCY_MARKERS:
            if urgency in text_normalized:
                score += 0.5

        if score > best_score:
            best_score = score
            best_match = (incident_type, config, keywords_matched)

    if best_score < 1:
        return None, 'moyenne', 0.0

    incident_type, config, _ = best_match

    # Déterminer la gravité
    gravite = config['default_gravite']
    for grave_kw in config['keywords_grave']:
        if grave_kw in text_normalized:
            # Augmenter d'un niveau
            if gravite == 'faible':
                gravite = 'moyenne'
            elif gravite == 'moyenne':
                gravite = 'haute'
            elif gravite == 'haute':
                gravite = 'critique'
            break

    # Urgence markers peuvent aussi augmenter
    for urgency in URGENCY_MARKERS:
        if urgency in text_normalized and gravite != 'critique':
            if gravite == 'faible':
                gravite = 'moyenne'
            elif gravite == 'moyenne':
                gravite = 'haute'
            break

    confidence = min(0.95, 0.3 + best_score * 0.15)

    return incident_type, gravite, confidence


def _extraire_parcelle(text_normalized: str) -> str:
    """Tente d'extraire le nom de parcelle/zone du texte."""
    import re as re_module

    for pattern in LOCALISATION_PATTERNS:
        match = re_module.search(pattern, text_normalized, re_module.IGNORECASE)
        if match:
            return match.group(1).strip() if match.groups() else match.group(0).strip()

    # Recherche simple de mots comme "parcelle A", "champ 3"
    simple_match = re_module.search(r'(?:parcelle|champ|zone|secteur)\s*([A-Z0-9]+)', text_normalized, re_module.IGNORECASE)
    if simple_match:
        return simple_match.group(0).strip()

    return ''


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
    """
    Enregistre un incident agricole signalé par voix.

    Args:
        ferme_id: UUID de la ferme concernée
        profile_id: UUID du profil utilisateur
        transcript_text: Texte transcrit de l'audio
        audio_url: URL du fichier audio stocké
        gps_lat: Latitude GPS
        gps_lon: Longitude GPS
        locale_hint: Langue/locale (fr, wo, ff)

    Returns:
        Payload avec détails de l'incident créé ou None si pas d'incident détecté
    """
    from baay.models import IncidentRapporte, Ferme, Profile

    text_normalized = _normalize_text(transcript_text)

    # Détecter le type d'incident
    incident_type, gravite, confidence = _detecter_type_incident(text_normalized)

    if not incident_type:
        logger.info("Aucun incident agricole détecté dans: %s", transcript_text[:100])
        return {
            "incident_detecte": False,
            "message": "Aucun incident agricole identifié dans le message vocal.",
            "transcript": transcript_text,
        }

    # Extraire parcelle
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
            "Incident vocal créé: type=%s, gravite=%s, ferme=%s, parcelle=%s",
            incident_type, gravite, ferme.nom, parcelle or "non précisée"
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
            "message": f"✓ Incident signalé: {incident.get_type_incident_display()} - {incident.get_gravite_detectee_display()}",
            "transcript": transcript_text,
            "confidence_detection": round(confidence, 2),
        }

    except Ferme.DoesNotExist:
        logger.error("Ferme introuvable: %s", ferme_id)
        return {"incident_detecte": False, "error": "ferme_introuvable"}
    except Profile.DoesNotExist:
        logger.error("Profile introuvable: %s", profile_id)
        return {"incident_detecte": False, "error": "profile_introuvable"}
    except Exception as e:
        logger.exception("Erreur création incident vocal")
        return {"incident_detecte": False, "error": str(e)}


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
    Pipeline vocal amélioré: STT → Détection Incident → RAG → TTS.

    Si un incident agricole est détecté, il est enregistré en base.
    Sinon, retourne une réponse RAG classique.

    Args:
        transcript_text: Texte transcrit
        locale_hint: Langue (fr, wo, ff)
        simulated_stt_confidence: Confiance STT simulée
        ferme_id: UUID ferme (optionnel, pour enregistrement incident)
        profile_id: UUID profil (optionnel, pour enregistrement incident)
        gps_lat: Latitude GPS
        gps_lon: Longitude GPS
    """
    text_normalized = _normalize_text(transcript_text)

    # ÉTAPE 1: Détection d'incident
    incident_type, gravite, confidence = _detecter_type_incident(text_normalized)

    # Si incident détecté ET contexte ferme disponible → enregistrer
    if incident_type and ferme_id and profile_id:
        incident_result = enregistrer_incident_vocal(
            ferme_id=ferme_id,
            profile_id=profile_id,
            transcript_text=transcript_text,
            gps_lat=gps_lat,
            gps_lon=gps_lon,
            locale_hint=locale_hint,
        )

        if incident_result.get("incident_detecte"):
            # Réponse spécifique incident
            reponse_incident = (
                f"🚨 Incident agricole signalé:\n"
                f"{incident_result['type_incident_display']} - {incident_result['gravite_display']}\n\n"
                f"✓ Votre signalement a été enregistré et transmis au responsable de la ferme.\n"
                f"Un suivi sera effectué dans les plus brefs délais."
            )

            return {
                "pipeline": [
                    {"step": "stt", "status": "simulated", "locale": locale_hint, "confidence": simulated_stt_confidence},
                    {"step": "incident_detection", "status": "detected", "type": incident_type, "gravite": gravite},
                    {"step": "incident_save", "status": "saved", "incident_id": incident_result.get("incident_id")},
                    {"step": "tts", "status": "incident_ack_stub", "voice_profile": "sahel_agronome_neutral"},
                ],
                "incident": incident_result,
                "answer_text": reponse_incident,
                "disclaimer": "Incident transmis aux responsables de la ferme.",
            }

    # ÉTAPE 2: Pipeline RAG classique si pas d'incident
    snippets = _rag_simulated_snippets(transcript_text)
    answer = _draft_answer(transcript_text, snippets, locale_hint)

    payload: dict[str, Any] = {
        "pipeline": [
            {"step": "stt", "status": "simulated", "locale": locale_hint, "confidence": simulated_stt_confidence},
            {"step": "incident_detection", "status": "none" if not incident_type else "detected_not_saved", "type": incident_type},
            {"step": "rag", "status": "stub", "snippets_used": len(snippets)},
            {"step": "tts", "status": "simulated_cloning_stub", "voice_profile": "sahel_agronome_neutral"},
        ],
        "system_directive_preview": SYSTEM_DIRECTIVE_SAHEL[:120] + "…",
        "transcript_normalized": text_normalized,
        "rag_snippets": snippets,
        "answer_text": answer,
        "disclaimer": "Réponse générée en mode simulation ; brancher STT/RAG/TTS réels avant production.",
    }

    if incident_type and not (ferme_id and profile_id):
        payload["incident_detected_but_not_saved"] = {
            "type": incident_type,
            "gravite": gravite,
            "reason": "Contexte ferme/utilisateur manquant",
        }

    logger.info("vocal_query_pipeline locale=%s incident=%s", locale_hint, incident_type or "none")
    return payload
