"""
Routeur d'intentions du copilote vocal (VUI) — (texte FR + contexte écran) → action JSON.

Tool-calling : le LLM agit en parseur d'intentions et renvoie EXCLUSIVEMENT un JSON
structuré. Le résultat est validé (allowlist de navigation, field_id réellement
présent à l'écran) avant d'être renvoyé à la vue. Aucune URL brute du LLM n'est suivie.
"""
from __future__ import annotations

import json
import logging

from django.conf import settings
from django.urls import NoReverseMatch, reverse

logger = logging.getLogger(__name__)

# Allowlist : phrases parlées → noms de routes navigables (anti open-redirect/hallucination).
# Noms d'URL vérifiés dans baay/urls*.py.
NAV_ALLOWLIST: dict[str, str] = {
    "tableau de bord": "dashboard",
    "accueil": "dashboard",
    "fermes": "liste_fermes",
    "mes fermes": "liste_fermes",
    "projets": "liste_projets",
    "mes projets": "liste_projets",
    "nouvelle ferme": "creer_ferme",
    "créer une ferme": "creer_ferme",
    "nouveau projet": "creer_projet",
    "créer un projet": "creer_projet",
}

_SYSTEM = """Tu es le routeur d'intentions d'un copilote vocal agricole, en français.
Tu reçois la phrase de l'utilisateur et le contexte de l'écran (URL, champs visibles).
Réponds STRICTEMENT par UN SEUL objet JSON, sans aucun texte autour, selon ce schéma :

{"action":"navigation","target":"<une clé EXACTE parmi: %(nav)s>","say":"<confirmation courte>"}
{"action":"fill_field","field_id":"<id EXACT d'un champ visible>","value":"<valeur>","say":"<question du champ suivant>"}
{"action":"submit","say":"<confirmation>"}
{"action":"speak","say":"<réponse ou aide>"}
{"action":"unknown","say":"<demande de reformulation>"}

Règles strictes :
- N'invente JAMAIS un field_id absent de la liste des champs visibles.
- Pour le slot-filling, choisis le PREMIER champ vide pertinent et formule dans "say" la question du champ suivant.
- Si la demande ne correspond à rien, renvoie "unknown".
- "say" est toujours en français, court."""


def parse_intent(transcript: str, context: dict) -> dict:
    """Interroge le LLM (JSON strict) puis valide l'action. Ne lève jamais : repli 'speak'."""
    field_ids = {f.get("id") for f in context.get("fields", []) if f.get("id")}
    user_msg = (
        f'Phrase: "{transcript}"\n'
        f'URL actuelle: {context.get("url")}\n'
        f'Champs visibles: {json.dumps(context.get("fields", []), ensure_ascii=False)}'
    )
    system = _SYSTEM % {"nav": ", ".join(NAV_ALLOWLIST)}

    try:
        raw = _llm_json(system, user_msg)
        action = json.loads(_extract_json(raw))
    except Exception as exc:  # noqa: BLE001 — jamais de 500 pour une commande vocale
        logger.warning("VUI parse_intent échec: %s", exc)
        return {"action": "speak", "say": "Je n'ai pas bien compris, pouvez-vous répéter ?"}

    return _validate(action, field_ids)


def _validate(action: dict, field_ids: set) -> dict:
    kind = action.get("action")
    if kind == "navigation":
        name = NAV_ALLOWLIST.get((action.get("target") or "").strip().lower())
        if not name:
            return {"action": "speak", "say": "Cette page n'est pas accessible par la voix."}
        try:
            action["url"] = reverse(name)
        except NoReverseMatch:
            logger.error("VUI: route '%s' introuvable", name)
            return {"action": "speak", "say": "Page introuvable."}
    elif kind == "fill_field":
        if action.get("field_id") not in field_ids:  # anti-hallucination
            return {"action": "speak", "say": "Je ne vois pas ce champ à l'écran."}
    elif kind not in ("submit", "speak", "unknown"):
        return {"action": "speak", "say": "Action non reconnue."}
    return action


def _extract_json(raw: str) -> str:
    """Isole le premier objet JSON d'une sortie LLM éventuellement bavarde."""
    raw = (raw or "").strip()
    start, end = raw.find("{"), raw.rfind("}")
    return raw[start:end + 1] if start != -1 and end != -1 else raw


def _llm_json(system: str, user: str) -> str:
    """Délègue au backend LLM configuré (réutilise les clients vocaux existants)."""
    backend = getattr(settings, "VOCAL_LLM_BACKEND", "gemini")
    if backend == "ollama":
        from baay.services.ollama_responder import generate_response
        return generate_response(user, system=system + "\nRéponds en JSON uniquement.")
    if backend == "deepseek":
        from baay.services.deepseek_responder import generate_response
        return generate_response(f"{system}\n\n{user}")
    from baay.services.gemini_vocal import generate_text
    return generate_text(user, system_text=system)
