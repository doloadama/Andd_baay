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


def run_vocal_query_pipeline(
    *,
    transcript_text: str,
    locale_hint: str = "fr",
    simulated_stt_confidence: float = 0.92,
) -> dict[str, Any]:
    """
    Simule STT → RAG → TTS et renvoie un payload JSON sérialisable.

    `transcript_text` correspond au texte déjà transcrit ; en prod, sera alimenté
    par un moteur STT dialectal puis filtré ici.
    """
    snippets = _rag_simulated_snippets(transcript_text)
    answer = _draft_answer(transcript_text, snippets, locale_hint)

    payload: dict[str, Any] = {
        "pipeline": [
            {"step": "stt", "status": "simulated", "locale": locale_hint, "confidence": simulated_stt_confidence},
            {"step": "rag", "status": "stub", "snippets_used": len(snippets)},
            {"step": "tts", "status": "simulated_cloning_stub", "voice_profile": "sahel_agronome_neutral"},
        ],
        "system_directive_preview": SYSTEM_DIRECTIVE_SAHEL[:120] + "…",
        "transcript_normalized": _normalize_text(transcript_text),
        "rag_snippets": snippets,
        "answer_text": answer,
        "disclaimer": "Réponse générée en mode simulation ; brancher STT/RAG/TTS réels avant production.",
    }
    logger.info("vocal_query_pipeline locale=%s len_transcript=%s", locale_hint, len(transcript_text or ""))
    return payload
