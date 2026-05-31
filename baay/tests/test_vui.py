# baay/tests/test_vui.py — Copilote vocal : VocalCommandView (pont HTMX) + orchestrateur.
import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase


class VocalCommandViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("vui", password="pass1234")
        self.client.force_login(self.user)
        self.url = "/vocal/command/"

    def _post(self, transcript="x", context=None):
        return self.client.post(self.url, {
            "transcript": transcript,
            "context": json.dumps(context or {"url": "/", "fields": []}),
        })

    def test_login_requis(self):
        self.client.logout()
        resp = self.client.post(self.url, {"transcript": "x"})
        self.assertIn(resp.status_code, (302, 403))

    def test_navigation_renvoie_hx_redirect(self):
        with patch("baay.views_vui.parse_intent",
                   return_value={"action": "navigation", "url": "/dashboard/", "say": "ok"}):
            resp = self._post("va sur le tableau de bord")
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp["HX-Redirect"], "/dashboard/")

    def test_fill_field_renvoie_hx_trigger(self):
        with patch("baay.views_vui.parse_intent",
                   return_value={"action": "fill_field", "field_id": "id_nom_ferme",
                                 "value": "Ferme du Sahel", "say": "Quelle superficie ?"}):
            resp = self._post("la ferme s'appelle Ferme du Sahel")
        self.assertEqual(resp.status_code, 204)
        trig = json.loads(resp["HX-Trigger"])
        self.assertIn("vuiFillField", trig)
        self.assertEqual(trig["vuiFillField"]["field_id"], "id_nom_ferme")
        self.assertEqual(trig["vuiFillField"]["value"], "Ferme du Sahel")

    def test_speak_renvoie_hx_trigger_vuispeak(self):
        with patch("baay.views_vui.parse_intent",
                   return_value={"action": "speak", "say": "Dites par exemple créer une ferme."}):
            resp = self._post("blabla")
        trig = json.loads(resp["HX-Trigger"])
        self.assertIn("vuiSpeak", trig)

    def test_transcript_vide(self):
        resp = self._post("   ")
        trig = json.loads(resp["HX-Trigger"])
        self.assertIn("vuiSpeak", trig)


class VuiOrchestratorTest(TestCase):

    def test_navigation_allowlist_resolue(self):
        from baay.services.vui_orchestrator import _validate
        a = _validate({"action": "navigation", "target": "Tableau de bord"}, set())
        self.assertEqual(a["action"], "navigation")
        self.assertEqual(a["url"], "/dashboard/")

    def test_navigation_hors_allowlist_rejetee(self):
        from baay.services.vui_orchestrator import _validate
        a = _validate({"action": "navigation", "target": "page secrète"}, set())
        self.assertEqual(a["action"], "speak")

    def test_fill_field_hallucine_rejete(self):
        from baay.services.vui_orchestrator import _validate
        a = _validate({"action": "fill_field", "field_id": "id_x"}, {"id_nom"})
        self.assertEqual(a["action"], "speak")

    def test_parse_intent_jamais_500(self):
        from baay.services import vui_orchestrator
        with patch.object(vui_orchestrator, "_llm_json", side_effect=RuntimeError("LLM down")):
            a = vui_orchestrator.parse_intent("test", {"fields": []})
        self.assertEqual(a["action"], "speak")  # repli gracieux
