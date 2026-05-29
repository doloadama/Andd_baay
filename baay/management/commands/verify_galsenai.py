"""
Diagnostic de disponibilité des modèles GalsenAI sur l'API HuggingFace.

Le risque principal de l'assistant vocal Wolof : l'API Inference serverless
(api-inference.huggingface.co) a été largement dépréciée pour les modèles
communautaires. Cette commande vérifie, token en main, si les modèles ASR/LLM
répondent vraiment — et classe chaque résultat sans ambiguïté.

Usage:
    python manage.py verify_galsenai
    python manage.py verify_galsenai --token hf_xxx   # override ponctuel
"""
from __future__ import annotations

import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

HF_BASE = "https://api-inference.huggingface.co/models"


class Command(BaseCommand):
    help = "Vérifie la disponibilité des modèles GalsenAI (ASR/LLM) sur HuggingFace serverless."

    def add_arguments(self, parser):
        parser.add_argument("--token", default=None, help="HF token (sinon settings.HF_API_TOKEN)")
        parser.add_argument("--timeout", type=int, default=25)

    def handle(self, *args, **opts):
        token = (opts["token"] or getattr(settings, "HF_API_TOKEN", "") or "").strip()
        timeout = opts["timeout"]

        if not token:
            self.stdout.write(self.style.ERROR(
                "[X] HF_API_TOKEN absent. Ajoutez-le dans .env "
                "(créez-en un sur https://huggingface.co/settings/tokens) puis relancez."
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Diagnostic GalsenAI — HuggingFace serverless\n"))

        llm = getattr(settings, "GALSENAI_LLM_MODEL", "galsenai/FineLlama-3.1-8B")
        asr = getattr(settings, "GALSENAI_ASR_MODEL", "galsenai/whisper-large-v3-wo")

        # LLM : test texte (le plus simple, prouve que la voie serverless marche)
        self._probe(
            label="LLM (réponse Wolof)",
            model=llm,
            token=token,
            timeout=timeout,
            json_body={"inputs": "Naka nga def?", "parameters": {"max_new_tokens": 8}},
        )
        # ASR : envoi d'un octet-stream minimal ; on lit le code, pas le contenu.
        self._probe(
            label="ASR (transcription audio)",
            model=asr,
            token=token,
            timeout=timeout,
            raw_body=b"\x00" * 32,
            content_type="audio/webm",
        )

        self.stdout.write(
            "\nLégende : "
            + self.style.SUCCESS("REACHABLE") + "=servi · "
            + self.style.WARNING("COLD_START") + "=servi mais démarre · "
            + self.style.ERROR("NOT_SERVED") + "=plus dispo en serverless (404) · "
            + "AUTH=token invalide"
        )

    def _probe(self, *, label, model, token, timeout, json_body=None, raw_body=None,
               content_type="application/json"):
        url = f"{HF_BASE}/{model}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": content_type}
        t0 = time.monotonic()
        try:
            if raw_body is not None:
                r = requests.post(url, headers=headers, data=raw_body, timeout=timeout)
            else:
                r = requests.post(url, headers=headers, json=json_body, timeout=timeout)
        except requests.Timeout:
            self._line(label, model, self.style.WARNING("COLD_START?"), "timeout (modèle probablement en démarrage)")
            return
        except requests.RequestException as exc:
            self._line(label, model, self.style.ERROR("RÉSEAU"), str(exc)[:80])
            return

        ms = int((time.monotonic() - t0) * 1000)
        code = r.status_code
        if code == 200:
            self._line(label, model, self.style.SUCCESS("REACHABLE"), f"HTTP 200 en {ms} ms")
        elif code == 503:
            try:
                est = r.json().get("estimated_time")
            except Exception:
                est = None
            self._line(label, model, self.style.WARNING("COLD_START"), f"503 — démarre (~{est}s), réessayez")
        elif code == 404:
            self._line(label, model, self.style.ERROR("NOT_SERVED"),
                       "404 — modèle absent du serverless. Migration nécessaire (Inference Endpoint / API GalsenAI).")
        elif code in (401, 403):
            self._line(label, model, self.style.ERROR("AUTH"), f"HTTP {code} — token invalide ou sans accès")
        else:
            body = (r.text or "")[:90].replace("\n", " ")
            self._line(label, model, self.style.WARNING(f"HTTP {code}"), body)

    def _line(self, label, model, verdict, detail):
        self.stdout.write(f"  {verdict:<24} {label:<28} {model}")
        self.stdout.write(f"          - {detail}")
