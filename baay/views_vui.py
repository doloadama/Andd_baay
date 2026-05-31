"""
Copilote vocal contextuel — endpoint d'orchestration.

Reçoit {transcript, context} depuis le navigateur (Web Speech API + snapshot écran)
et renvoie une réponse HTMX pilotant l'UI :
  - HX-Redirect            → navigation vocale instantanée
  - HX-Trigger vuiFillField → remplissage de champ (slot-filling)
  - HX-Trigger vuiSubmit    → soumission de formulaire
  - HX-Trigger vuiSpeak     → l'assistant "lit" / guide (SpeechSynthesis côté client)
"""
from __future__ import annotations

import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import View

from baay.services.vui_orchestrator import parse_intent

logger = logging.getLogger(__name__)


class VocalCommandView(LoginRequiredMixin, View):
    """POST {transcript, context} → réponse HTMX (HX-Redirect / HX-Trigger)."""

    def post(self, request, *args, **kwargs):
        transcript = (request.POST.get("transcript") or "").strip()
        try:
            context = json.loads(request.POST.get("context") or "{}")
        except (json.JSONDecodeError, TypeError):
            context = {}

        if not transcript:
            return self._speak("Je n'ai rien entendu.")

        action = parse_intent(transcript, context)
        kind = action.get("action")
        logger.info("VUI commande: '%s' → %s", transcript[:60], kind)

        if kind == "navigation":
            resp = HttpResponse(status=204)
            resp["HX-Redirect"] = action["url"]
            return resp
        if kind == "fill_field":
            return self._trigger("vuiFillField", {
                "field_id": action["field_id"],
                "value": action.get("value", ""),
                "say": action.get("say", ""),
            })
        if kind == "submit":
            return self._trigger("vuiSubmit", {"say": action.get("say", "")})
        # speak / unknown
        return self._speak(action.get("say", "Je n'ai pas compris."))

    @staticmethod
    def _trigger(event: str, data: dict) -> HttpResponse:
        resp = HttpResponse(status=204)
        resp["HX-Trigger"] = json.dumps({event: data})
        return resp

    def _speak(self, text: str) -> HttpResponse:
        return self._trigger("vuiSpeak", {"say": text})
