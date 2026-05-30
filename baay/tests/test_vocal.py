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


# ══════════════════════════════════════════════════════════════════════════════
# Client STT local (whisper_local) + backend hybride de la tâche
# ══════════════════════════════════════════════════════════════════════════════

class WhisperLocalClientTest(TestCase):

    @override_settings(WHISPER_STT_URL="")
    def test_url_absente_leve_NotConfigured(self):
        from baay.services.whisper_local import transcribe_audio, WhisperLocalNotConfigured
        with self.assertRaises(WhisperLocalNotConfigured):
            transcribe_audio(b"audio", "audio/webm")

    @override_settings(WHISPER_STT_URL="http://stt:9000")
    def test_succes_retourne_transcript(self):
        from baay.services import whisper_local
        resp = MagicMock(); resp.json.return_value = {"transcript": "Naka nga def", "duration_ms": 42}
        resp.raise_for_status.return_value = None
        with patch.object(whisper_local.requests, "post", return_value=resp):
            txt = whisper_local.transcribe_audio(b"audio", "audio/wav")
        self.assertEqual(txt, "Naka nga def")

    @override_settings(WHISPER_STT_URL="http://stt:9000")
    def test_service_injoignable_leve_WhisperLocalError(self):
        from baay.services import whisper_local
        import requests as _rq
        with patch.object(whisper_local.requests, "post", side_effect=_rq.ConnectionError("refused")):
            with self.assertRaises(whisper_local.WhisperLocalError):
                whisper_local.transcribe_audio(b"audio", "audio/wav")


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False,
                   VOCAL_STT_BACKEND="whisper_local", VOCAL_FAQ_FIRST=False)
class HybridBackendTaskTest(TestCase):

    def setUp(self):
        cache.clear()
        self.key = "vocal_task:hyb"

    def test_backend_whisper_local_transcrit_puis_repond(self):
        from baay.tasks.vocal import process_vocal_task
        with patch("baay.services.whisper_local.transcribe_audio", return_value="Kañ laa ji dugub") as mk_stt, \
             patch("baay.tasks.vocal.generate_response_from_text", return_value="Su naka tey...") as mk_llm:
            process_vocal_task.apply(args=[b"a".hex(), "audio/webm", self.key])
            data = cache.get(self.key)
        self.assertEqual(data["status"], "done")
        self.assertEqual(data["result"]["transcript"], "Kañ laa ji dugub")
        self.assertEqual(data["result"]["response"], "Su naka tey...")
        mk_stt.assert_called_once()
        mk_llm.assert_called_once_with("Kañ laa ji dugub")

    def test_backend_whisper_local_indisponible(self):
        from baay.tasks.vocal import process_vocal_task
        from baay.services.whisper_local import WhisperLocalError
        with patch("baay.services.whisper_local.transcribe_audio",
                   side_effect=WhisperLocalError("down")):
            process_vocal_task.apply(args=[b"a".hex(), "audio/webm", self.key])
            data = cache.get(self.key)
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["code"], "stt_unavailable")


# ══════════════════════════════════════════════════════════════════════════════
# FAQ Wolof locale + chemins hybrides (FAQ-first / repli cloud / fallback)
# ══════════════════════════════════════════════════════════════════════════════

class WolofFaqTest(TestCase):

    def test_intention_reconnue_renvoie_reponse(self):
        from baay.services.wolof_faq import match_response
        self.assertIsNotNone(match_response("naka nga def"))          # salutation
        self.assertIsNotNone(match_response("kañ laa wara ji dugub")) # semis_mil (2 hits)

    def test_aucune_intention_renvoie_none(self):
        from baay.services.wolof_faq import match_response
        self.assertIsNone(match_response("xyzzy qwerty zzz"))
        self.assertIsNone(match_response(""))


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False,
                   VOCAL_STT_BACKEND="whisper_local", VOCAL_FAQ_FIRST=True,
                   VOCAL_OFFLINE_FALLBACK=True)
class HybridFaqTaskTest(TestCase):

    def setUp(self):
        cache.clear()
        self.key = "vocal_task:faq"

    def test_faq_repond_sans_appeler_le_cloud(self):
        from baay.tasks.vocal import process_vocal_task
        with patch("baay.services.whisper_local.transcribe_audio", return_value="naka nga def"), \
             patch("baay.tasks.vocal.generate_response_from_text") as mk_llm:
            process_vocal_task.apply(args=[b"a".hex(), "audio/webm", self.key])
            data = cache.get(self.key)
        self.assertEqual(data["status"], "done")
        self.assertTrue(data["result"]["response"])
        mk_llm.assert_not_called()  # FAQ a court-circuité le cloud

    def test_question_ouverte_passe_au_cloud(self):
        from baay.tasks.vocal import process_vocal_task
        with patch("baay.services.whisper_local.transcribe_audio", return_value="xyzzy question ouverte"), \
             patch("baay.tasks.vocal.generate_response_from_text", return_value="réponse LLM") as mk_llm:
            process_vocal_task.apply(args=[b"a".hex(), "audio/webm", self.key])
            data = cache.get(self.key)
        self.assertEqual(data["result"]["response"], "réponse LLM")
        mk_llm.assert_called_once()

    def test_cloud_indispo_retombe_sur_fallback_wolof(self):
        from baay.tasks.vocal import process_vocal_task
        from baay.services.gemini_vocal import GeminiVocalRateLimited
        from baay.services.wolof_faq import FALLBACK_WO
        with patch("baay.services.whisper_local.transcribe_audio", return_value="xyzzy question ouverte"), \
             patch("baay.tasks.vocal.generate_response_from_text",
                   side_effect=GeminiVocalRateLimited("quota")):
            process_vocal_task.apply(args=[b"a".hex(), "audio/webm", self.key])
            data = cache.get(self.key)
        self.assertEqual(data["status"], "done")
        self.assertEqual(data["result"]["response"], FALLBACK_WO)


# ══════════════════════════════════════════════════════════════════════════════
# Client Ollama + backend LLM local
# ══════════════════════════════════════════════════════════════════════════════

class OllamaClientTest(TestCase):

    @override_settings(OLLAMA_URL="", OLLAMA_MODEL="")
    def test_non_configure_leve_OllamaNotConfigured(self):
        from baay.services.ollama_responder import generate_response, OllamaNotConfigured
        with self.assertRaises(OllamaNotConfigured):
            generate_response("test")

    @override_settings(OLLAMA_URL="http://ollama:11434", OLLAMA_MODEL="finellama-wolof")
    def test_succes_retourne_reponse(self):
        from baay.services import ollama_responder
        resp = MagicMock()
        resp.json.return_value = {"message": {"content": "Dugub day ji ci nawet"}}
        resp.raise_for_status.return_value = None
        with patch.object(ollama_responder.requests, "post", return_value=resp):
            result = ollama_responder.generate_response("kañ laa ji dugub")
        self.assertEqual(result, "Dugub day ji ci nawet")

    @override_settings(OLLAMA_URL="http://ollama:11434", OLLAMA_MODEL="finellama-wolof")
    def test_service_down_leve_OllamaError(self):
        from baay.services import ollama_responder
        import requests as _rq
        with patch.object(ollama_responder.requests, "post", side_effect=_rq.ConnectionError("refused")):
            with self.assertRaises(ollama_responder.OllamaError):
                ollama_responder.generate_response("test")


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False,
                   VOCAL_STT_BACKEND="whisper_local", VOCAL_LLM_BACKEND="ollama",
                   VOCAL_FAQ_FIRST=False, VOCAL_OFFLINE_FALLBACK=True)
class OllamaBackendTaskTest(TestCase):

    def setUp(self):
        cache.clear()
        self.key = "vocal_task:oll"

    def test_ollama_repond(self):
        from baay.tasks.vocal import process_vocal_task
        with patch("baay.services.whisper_local.transcribe_audio", return_value="question"), \
             patch("baay.services.ollama_responder.generate_response", return_value="réponse locale"):
            process_vocal_task.apply(args=[b"a".hex(), "audio/webm", self.key])
            data = cache.get(self.key)
        self.assertEqual(data["status"], "done")
        self.assertEqual(data["result"]["response"], "réponse locale")

    def test_ollama_indispo_fallback_wolof(self):
        from baay.tasks.vocal import process_vocal_task
        from baay.services.ollama_responder import OllamaError
        from baay.services.wolof_faq import FALLBACK_WO
        with patch("baay.services.whisper_local.transcribe_audio", return_value="question"), \
             patch("baay.services.ollama_responder.generate_response",
                   side_effect=OllamaError("down")):
            process_vocal_task.apply(args=[b"a".hex(), "audio/webm", self.key])
            data = cache.get(self.key)
        self.assertEqual(data["status"], "done")
        self.assertEqual(data["result"]["response"], FALLBACK_WO)
