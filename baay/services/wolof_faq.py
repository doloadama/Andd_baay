"""
Répondeur d'intentions agricoles Wolof — local, in-process, hors-ligne.

Approche déterministe (mots-clés) : pas de LLM, pas de réseau, réponse en
millisecondes. Couvre les questions agricoles récurrentes ; les questions ouvertes
retombent sur le LLM cloud (Gemini). Sert aussi de mode démo / fallback hors-ligne.

⚠️ Le contenu Wolof ci-dessous est un SEED à faire valider/enrichir par un
locuteur natif et un agronome. La logique de matching, elle, est définitive.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field


def _normalize(text: str) -> str:
    """minuscule + sans accents + espaces compacts (matching robuste FR/Wolof)."""
    text = (text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return " ".join(text.split())


@dataclass(frozen=True)
class Intent:
    name: str
    keywords: tuple           # déclencheurs (normalisés à la comparaison)
    response_wo: str          # réponse en Wolof (SEED — à valider)
    min_hits: int = 1         # nb de mots-clés requis pour déclencher


# ── Base d'intentions (SEED — à enrichir) ───────────────────────────────────
INTENTS: list[Intent] = [
    Intent(
        name="salutation",
        keywords=("salamaalekum", "assalaa", "nanga def", "naka nga def", "jamm", "bonjour"),
        response_wo="Salaamaalekum ! Maa ngi fi, Jëf Baay. Lan laa la mën a dimbali ci sa mbay ?",
    ),
    Intent(
        name="semis_mil",
        keywords=("ji", "dugub", "mil", "ñebbe", "semer", "semis", "kañ", "jëmm"),
        response_wo="Dugub day ji ci ndoorteel nawet bi, ci diggante 15 ak 30 juin su taw bi agsi. "
                    "Wëraleel suuf si bu baax bala ngay ji.",
        min_hits=2,
    ),
    Intent(
        name="maladie_ravageur",
        keywords=("tawat", "feebar", "wenn", "jangoro", "maladie", "ravageur", "chenille", "insecte", "xob"),
        response_wo="Su sa mbay am na tawat, nataalal xob yi te yónnee ko ci BaayVision ngir xam jangoro ji "
                    "ak garab gi ko war. Bul jëfandikoo doomu garab te xamuloo ko.",
    ),
    Intent(
        name="prix_marche",
        keywords=("njëg", "prix", "marse", "marche", "jaay", "jënd", "cfa", "franc"),
        response_wo="Njëg yi ci marse yi dañuy soppiku. Seetal xët 'Njëg marse yi' ci app bi ngir gis "
                    "njëgu sa mbay ci béb fan.",
    ),
    Intent(
        name="meteo_pluie",
        keywords=("taw", "asamaan", "ngelaw", "pluie", "meteo", "tawaat", "naaj"),
        response_wo="Seetal widget 'Asamaan' ci sa tablo ngir xam ndax taw bi dina dal ci ëllëg. "
                    "Bul ji bala taw bi.",
    ),
    Intent(
        name="arrosage_eau",
        keywords=("ndox", "tooyal", "arroser", "eau", "irrigation", "sédd"),
        response_wo="Tooyal sa mbay ci suba ak ngoon, bul ko def ci naaj wi tàng. "
                    "Mbay mi soxla na ndox waaye bul ko fees.",
        min_hits=1,
    ),
    Intent(
        name="engrais",
        keywords=("engrais", "angare", "fertilisant", "compost", "suufu", "nped"),
        response_wo="Jëfandikoo engrais bu jaar yoon (NPK walla compost) ci jamono ju baax. "
                    "Topptoo li ñu bind ci pakk bi, bul ko épp.",
    ),
]

# Réponse par défaut quand aucune intention ne matche et qu'on ne veut pas (ou peut pas)
# appeler le cloud.
FALLBACK_WO = (
    "Baal ma, dégguma bu baax sa laaj. Mën nga ko waxaat walla bind ko ? "
    "Mën nga it laaj ci wàllu ji, tawat, njëg marse, walla asamaan."
)


def match_response(transcript: str) -> str | None:
    """
    Retourne une réponse Wolof si une intention agricole est reconnue, sinon None
    (→ l'appelant peut alors tenter le LLM cloud).
    """
    norm = _normalize(transcript)
    if not norm:
        return None
    best: tuple[int, Intent] | None = None
    for intent in INTENTS:
        hits = sum(1 for kw in intent.keywords if _normalize(kw) in norm)
        if hits >= intent.min_hits:
            if best is None or hits > best[0]:
                best = (hits, intent)
    return best[1].response_wo if best else None
