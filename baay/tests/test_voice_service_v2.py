# baay/tests/test_voice_service_v2.py
# Tests du service vocal modulaire (Strategy + incident-first + pont NLLB).
from unittest.mock import patch

from django.test import TestCase, override_settings

import baay.voice_assistant_service as v


class IncidentDetectionTest(TestCase):
    def test_invasion_critique(self):
        t, g, c = v._detecter_type_incident(
            v._normalize_text("Urgent ! invasion de criquets, tout mangé dans le champ"))
        self.assertEqual(t, "invasion_ravageurs")
        self.assertEqual(g, "critique")
        self.assertGreater(c, 0.5)

    def test_aucun_incident(self):
        t, _, c = v._detecter_type_incident(v._normalize_text("Bonjour, comment semer le mil ?"))
        self.assertIsNone(t)
        self.assertEqual(c, 0.0)


@override_settings(VOCAL_STT_BACKEND="simulated", VOCAL_TTS_BACKEND="simulated",
                   VOCAL_TRANSLATION_BRIDGE=False)
class LLMDispatchTest(TestCase):

    @override_settings(VOCAL_LLM_BACKEND="gemini")
    def test_backend_gemini_appelle_generate_text(self):
        with patch("baay.services.gemini_vocal.generate_text", return_value="réponse FR") as mk:
            out = v._llm_answer_fr("Comment lutter contre la rouille ?")
        mk.assert_called_once()
        self.assertEqual(out, "réponse FR")

    @override_settings(VOCAL_LLM_BACKEND="ollama")
    def test_backend_ollama_appelle_generate_response(self):
        with patch("baay.services.ollama_responder.generate_response", return_value="rep ollama") as mk:
            out = v._llm_answer_fr("question")
        mk.assert_called_once()
        self.assertEqual(out, "rep ollama")

    @override_settings(VOCAL_LLM_BACKEND="gemini")
    def test_llm_en_echec_retombe_sur_simule(self):
        with patch("baay.services.gemini_vocal.generate_text", side_effect=RuntimeError("503")):
            out = v._llm_answer_fr("Comment lutter contre la rouille du mil ?")
        self.assertTrue(out)  # réponse simulée non vide, jamais d'exception remontée

    @override_settings(VOCAL_LLM_BACKEND="simulated")
    def test_backend_simulated(self):
        out = v._llm_answer_fr("irrigation goutte à goutte")
        self.assertIn("Conseils", out)


@override_settings(VOCAL_STT_BACKEND="simulated", VOCAL_LLM_BACKEND="simulated",
                   VOCAL_TTS_BACKEND="simulated", VOCAL_TRANSLATION_BRIDGE=True)
class TranslationBridgeTest(TestCase):

    def test_locale_wo_traduit_aller_retour(self):
        with patch("baay.services.galsenai_service.wolof_to_french", return_value="question FR") as mk_in, \
             patch("baay.services.galsenai_service.french_to_wolof", return_value="réponse WO") as mk_out:
            res = v.respond_stage(transcript_text="laaj ci wolof", locale_hint="wo")
        mk_in.assert_called_once()
        mk_out.assert_called_once()
        self.assertEqual(res.answer_text, "réponse WO")
        self.assertTrue(any(s.get("step") == "translate_in" and s.get("wo2fr") for s in res.pipeline))

    def test_locale_fr_pas_de_traduction(self):
        with patch("baay.services.galsenai_service.wolof_to_french") as mk_in:
            v.respond_stage(transcript_text="question en français", locale_hint="fr")
        mk_in.assert_not_called()


@override_settings(VOCAL_STT_BACKEND="simulated", VOCAL_LLM_BACKEND="simulated",
                   VOCAL_TTS_BACKEND="simulated", VOCAL_TRANSLATION_BRIDGE=False)
class IncidentFirstTest(TestCase):

    def test_incident_court_circuite_le_llm(self):
        fake_incident = {
            "incident_detecte": True, "incident_id": "abc",
            "type_incident_display": "Invasion de ravageurs", "gravite_display": "Critique",
        }
        with patch("baay.voice_assistant_service.enregistrer_incident_vocal", return_value=fake_incident), \
             patch("baay.voice_assistant_service._llm_answer_fr") as mk_llm:
            res = v.respond_stage(
                transcript_text="invasion de criquets urgent", locale_hint="fr",
                ferme_id="f1", profile_id="p1",
            )
        mk_llm.assert_not_called()  # incident-first : pas d'appel LLM
        self.assertIsNotNone(res.incident)
        self.assertTrue(res.incident["incident_detecte"])
        self.assertTrue(any(s.get("step") == "llm" and s.get("status") == "skipped_incident_ack"
                            for s in res.pipeline))


class BackwardCompatTest(TestCase):

    @override_settings(VOCAL_LLM_BACKEND="simulated", VOCAL_TRANSLATION_BRIDGE=False)
    def test_run_vocal_query_pipeline_contrat(self):
        p = v.run_vocal_query_pipeline(transcript_text="comment semer le mil", locale_hint="fr")
        # clés attendues par la vue
        for k in ("answer_text", "pipeline", "transcript_normalized", "system_directive_preview"):
            self.assertIn(k, p)
        self.assertTrue(p["answer_text"])
