# baay/tests/test_voice_command.py
# Copilote vocal (système existant api_voice_command) + extension slot-filling.
import json
import re

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase, override_settings


@override_settings(VOICE_RATE_LIMIT={"max_requests": 1000, "window_seconds": 60},
                   SECURE_SSL_REDIRECT=False)
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

    def test_recherche_vocale_ne_crashe_pas_sans_route_globale(self):
        resp = self._cmd("cherche mil")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["action"], "speak")
        self.assertIn("recherche vocale globale", data["message"].lower())

    def test_commande_accepte_token_csrf_rendu_dans_la_page(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        page = csrf_client.get("/")
        token_match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            page.content.decode(),
        )
        self.assertIsNotNone(token_match)

        resp = csrf_client.post(
            self.url,
            {"text": "va au tableau de bord"},
            HTTP_X_CSRFTOKEN=token_match.group(1),
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["action"], "redirect")

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
