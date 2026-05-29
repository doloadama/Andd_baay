# baay/tests/test_vocal.py
# ── Tests du pipeline vocal Wolof (Gemini) — 100% mocké, sans réseau ni quota ──
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from baay.services.gemini_vocal import (
    GeminiVocalError,
    GeminiVocalNotConfigured,
    GeminiVocalRateLimited,
    process_vocal_wolof,
)


def _fake_client(text=None, side_effect=None):
    """Construit un faux genai.Client dont generate_content renvoie `text` ou lève `side_effect`."""
    client = MagicMock()
    if side_effect is not None:
        client.models.generate_content.side_effect = side_effect
    else:
        client.models.generate_content.return_value = SimpleNamespace(text=text)
    return client


# ══════════════════════════════════════════════════════════════════════════════
# Service gemini_vocal.process_vocal_wolof
# ══════════════════════════════════════════════════════════════════════════════

@override_settings(GEMINI_API_KEYS=["test-key"], GEMINI_USE_VERTEX=False)
class GeminiVocalServiceTest(TestCase):

    def test_succes_retourne_transcript_et_reponse(self):
        client = _fake_client(text='{"transcript": "Naka ngay def", "response": "Jamm rekk"}')
        with patch("baay.services.gemini_vocal.genai.Client", return_value=client):
            res = process_vocal_wolof(b"audio-bytes", "audio/wav")
        self.assertEqual(res["transcript"], "Naka ngay def")
        self.assertEqual(res["response"], "Jamm rekk")

    def test_rate_limit_leve_GeminiVocalRateLimited(self):
        client = _fake_client(side_effect=Exception("429 RESOURCE_EXHAUSTED quota"))
        with patch("baay.services.gemini_vocal.genai.Client", return_value=client):
            with self.assertRaises(GeminiVocalRateLimited):
                process_vocal_wolof(b"audio", "audio/wav")

    def test_json_invalide_leve_GeminiVocalError(self):
        client = _fake_client(text="ceci n'est pas du JSON")
        with patch("baay.services.gemini_vocal.genai.Client", return_value=client):
            with self.assertRaises(GeminiVocalError):
                process_vocal_wolof(b"audio", "audio/wav")

    def test_reponse_vide_leve_GeminiVocalError(self):
        client = _fake_client(text='{"transcript": "x", "response": ""}')
        with patch("baay.services.gemini_vocal.genai.Client", return_value=client):
            with self.assertRaises(GeminiVocalError):
                process_vocal_wolof(b"audio", "audio/wav")

    def test_mime_non_supporte_retombe_sur_webm(self):
        client = _fake_client(text='{"transcript": "a", "response": "b"}')
        with patch("baay.services.gemini_vocal.genai.Client", return_value=client):
            process_vocal_wolof(b"audio", "audio/x-exotic")
        # Le mime passé à Part.from_bytes doit être normalisé (webm), pas l'exotique.
        _, kwargs = client.models.generate_content.call_args
        parts = kwargs["contents"][0].parts
        audio_part = parts[-1]
        # google.genai range les bytes dans inline_data.mime_type
        mime = getattr(getattr(audio_part, "inline_data", None), "mime_type", None)
        self.assertEqual(mime, "audio/webm")


@override_settings(GEMINI_API_KEYS=[], GEMINI_API_KEY="", GEMINI_USE_VERTEX=False)
class GeminiVocalNotConfiguredTest(TestCase):

    def test_sans_cle_ni_vertex_leve_NotConfigured(self):
        with self.assertRaises(GeminiVocalNotConfigured):
            process_vocal_wolof(b"audio", "audio/wav")


@override_settings(GEMINI_USE_VERTEX=True, GOOGLE_CLOUD_PROJECT="mon-projet",
                   GEMINI_VERTEX_LOCATION="us-central1")
class GeminiVocalVertexTest(TestCase):

    def test_mode_vertex_initialise_client_avec_region(self):
        client = _fake_client(text='{"transcript": "a", "response": "b"}')
        with patch("baay.services.gemini_vocal.genai.Client", return_value=client) as mk:
            res = process_vocal_wolof(b"audio", "audio/wav")
        self.assertEqual(res["response"], "b")
        # Le client doit être construit en mode Vertex, région US, sans clé API.
        _, kwargs = mk.call_args
        self.assertTrue(kwargs.get("vertexai"))
        self.assertEqual(kwargs.get("project"), "mon-projet")
        self.assertEqual(kwargs.get("location"), "us-central1")
        self.assertNotIn("api_key", kwargs)


# ══════════════════════════════════════════════════════════════════════════════
# Tâche Celery process_vocal_task (exécution eager)
# ══════════════════════════════════════════════════════════════════════════════

@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False)
class ProcessVocalTaskTest(TestCase):

    def setUp(self):
        cache.clear()
        self.key = "vocal_task:test123"
        self.audio_hex = b"fake-audio".hex()

    def _run(self):
        from baay.tasks.vocal import process_vocal_task
        process_vocal_task.apply(args=[self.audio_hex, "audio/wav", self.key])
        return cache.get(self.key)

    def test_succes_met_resultat_en_cache(self):
        with patch("baay.tasks.vocal.process_vocal_wolof",
                   return_value={"transcript": "t", "response": "r"}):
            data = self._run()
        self.assertEqual(data["status"], "done")
        self.assertEqual(data["result"]["response"], "r")
        self.assertEqual(data["result"]["transcript"], "t")
        self.assertFalse(data["result"]["tts_available"])

    def test_non_configure_met_erreur_not_configured(self):
        with patch("baay.tasks.vocal.process_vocal_wolof",
                   side_effect=GeminiVocalNotConfigured("no key")):
            data = self._run()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["code"], "not_configured")

    def test_erreur_api_met_erreur_api_error(self):
        with patch("baay.tasks.vocal.process_vocal_wolof",
                   side_effect=GeminiVocalError("boom")):
            data = self._run()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["code"], "api_error")


# ══════════════════════════════════════════════════════════════════════════════
# Vues
# ══════════════════════════════════════════════════════════════════════════════

class VocalViewsTest(TestCase):

    def test_get_page_rend_200(self):
        resp = self.client.get("/assistant-vocal/")
        self.assertEqual(resp.status_code, 200)

    def test_post_sans_audio_renvoie_400(self):
        resp = self.client.post("/assistant-vocal/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"], "no_audio")

    def test_result_inconnu_renvoie_410(self):
        resp = self.client.get("/assistant-vocal/result/inexistant/")
        self.assertEqual(resp.status_code, 410)
        self.assertEqual(resp.json()["status"], "expired")

    def test_result_pending_renvoie_le_statut(self):
        cache.set("vocal_task:abc", {"status": "pending"}, 60)
        resp = self.client.get("/assistant-vocal/result/abc/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "pending")
