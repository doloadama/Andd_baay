# baay/tests/test_voice_command.py
# Copilote vocal (système existant api_voice_command) + extension slot-filling.
import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings


@override_settings(VOICE_RATE_LIMIT={"max_requests": 1000, "window_seconds": 60})
class VoiceCommandTest(TestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("voix", password="pass1234")
        self.client.force_login(self.user)
        self.url = "/api/voice/command/"

    def _cmd(self, text, context=None):
        body = {"text": text}
        if context is not None:
            body["context"] = json.dumps(context)
        return self.client.post(self.url, body)

    # ── Navigation existante (non régressée) ────────────────────────────────
    def test_navigation_dashboard(self):
        data = self._cmd("va au tableau de bord").json()
        self.assertEqual(data["action"], "redirect")
        self.assertEqual(data["redirect"], "/dashboard/")

    def test_fallback_sans_contexte(self):
        data = self._cmd("xyzzy blabla").json()
        self.assertEqual(data["action"], "speak")

    # ── Slot-filling (nouveau) ──────────────────────────────────────────────
    def test_fill_premier_champ_vide(self):
        ctx = {"url": "/fermes/creer/", "focused_id": None, "fields": [
            {"id": "id_nom", "type": "text", "label": "Nom de la ferme", "filled": False},
            {"id": "id_superficie", "type": "number", "label": "Superficie", "filled": False},
        ]}
        data = self._cmd("Bambey Sérère", context=ctx).json()
        self.assertEqual(data["action"], "fill_field")
        self.assertEqual(data["field_id"], "id_nom")
        self.assertEqual(data["value"], "Bambey Sérère")     # casse préservée
        self.assertIn("Superficie", data["message"])         # guide le champ suivant

    def test_fill_cible_le_champ_focalise(self):
        ctx = {"url": "/fermes/creer/", "focused_id": "id_superficie", "fields": [
            {"id": "id_nom", "type": "text", "label": "Nom", "filled": True},
            {"id": "id_superficie", "type": "number", "label": "Superficie", "filled": False},
        ]}
        data = self._cmd("douze hectares", context=ctx).json()
        self.assertEqual(data["action"], "fill_field")
        self.assertEqual(data["field_id"], "id_superficie")

    def test_navigation_prioritaire_sur_fill(self):
        # Une commande connue reste interprétée comme navigation, même sur un formulaire.
        ctx = {"fields": [{"id": "id_nom", "type": "text", "label": "Nom", "filled": False}]}
        data = self._cmd("va au tableau de bord", context=ctx).json()
        self.assertEqual(data["action"], "redirect")

    def test_pas_de_champ_dictable_renvoie_speak(self):
        ctx = {"fields": [{"id": "id_actif", "type": "checkbox", "label": "Actif", "filled": False}]}
        data = self._cmd("zzz inconnu", context=ctx).json()
        self.assertEqual(data["action"], "speak")


@override_settings(VOICE_RATE_LIMIT={"max_requests": 1000, "window_seconds": 60},
                   VOCAL_LLM_BACKEND="deepseek", VOCAL_TRANSLATION_BRIDGE=True)
class VocalQueryApiTest(TestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("query-voice", password="pass1234")
        self.client.force_login(self.user)
        self.url = "/api/vocal-query/"

    def test_api_vocal_query_reste_local_par_defaut(self):
        payload = {"text": "kañ laa wara ji dugub", "locale_hint": "wo"}

        with patch("baay.services.deepseek_responder.generate_response") as mk_llm, \
             patch("baay.services.galsenai_service.wolof_to_french") as mk_to_fr, \
             patch("baay.services.galsenai_service.french_to_wolof") as mk_to_wo:
            response = self.client.post(
                self.url,
                data=json.dumps(payload),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["answer_text"])
        mk_llm.assert_not_called()
        mk_to_fr.assert_not_called()
        mk_to_wo.assert_not_called()
        self.assertTrue(any(
            s.get("step") == "llm"
            and s.get("backend") == "simulated"
            and s.get("status") == "external_disabled"
            for s in data["pipeline"]
        ))
