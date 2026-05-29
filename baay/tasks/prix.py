# baay/tasks/prix.py
"""
Tâches Celery pour la collecte des prix agricoles et la détection de variations.

  fetch_prix_marche_task   — toutes les 12 h
      FAO FPMA API (primaire) → OMA Sénégal (fallback si < 3 produits SEN)

  detecter_alertes_prix_task — quotidien 06 h 00
      Détecte les variations ≥ 15 % / 7 j et ≥ 20 % / 30 j,
      crée des AlertePrix idempotentes.
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)

_LOCK_FETCH   = "fetch_prix_marche_lock"
_LOCK_DETECT  = "detecter_alertes_prix_lock"
_LOCK_TTL     = 3600   # 1 h max par exécution


@shared_task(
    name="baay.tasks.fetch_prix_marche_task",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def fetch_prix_marche_task(self) -> dict:
    """
    Collecte les prix agricoles :
      1. FAO FPMA API (SEN)
      2. OMA Sénégal si FAO retourne < 3 produits distincts
    """
    if not cache.add(_LOCK_FETCH, "1", _LOCK_TTL):
        logger.info("fetch_prix_marche_task déjà en cours — ignoré.")
        return {"status": "skipped", "raison": "lock actif"}

    try:
        from baay.services.prix_service import (
            PrixServiceUnavailable,
            fetch_prix_fao_fpma,
            fetch_prix_oma,
        )
        from baay.models import PrixMarche
        from django.db.models import Count

        # ── Étape 1 : FAO FPMA ──────────────────────────────────────────────
        fao_crees = fao_maj = 0
        try:
            fao_crees, fao_maj = fetch_prix_fao_fpma(pays="SEN")
        except Exception as exc:
            logger.warning("FAO FPMA échoué : %s", exc)

        # Compter le nombre de produits distincts en base (SEN, 7 derniers jours)
        from datetime import date, timedelta
        produits_fao = (
            PrixMarche.objects
            .filter(source=PrixMarche.SOURCE_FAO_FPMA, date_relevee__gte=date.today() - timedelta(days=7))
            .values("produit_nom")
            .distinct()
            .count()
        )

        # ── Étape 2 : OMA fallback si peu de données FAO ────────────────────
        oma_crees = oma_maj = 0
        if produits_fao < 3:
            logger.info(
                "FAO FPMA : seulement %d produits SEN — activation OMA fallback.",
                produits_fao,
            )
            try:
                oma_crees, oma_maj = fetch_prix_oma()
            except PrixServiceUnavailable as exc:
                logger.warning("OMA Sénégal indisponible : %s", exc)
            except Exception as exc:
                logger.warning("OMA Sénégal erreur inattendue : %s", exc)

        result = {
            "status":    "ok",
            "fao_crees": fao_crees,
            "fao_maj":   fao_maj,
            "oma_crees": oma_crees,
            "oma_maj":   oma_maj,
            "produits_fao_7j": produits_fao,
        }
        logger.info("fetch_prix_marche_task terminé : %s", result)
        return result

    except Exception as exc:
        logger.exception("fetch_prix_marche_task erreur critique : %s", exc)
        raise self.retry(exc=exc)

    finally:
        cache.delete(_LOCK_FETCH)


@shared_task(
    name="baay.tasks.detecter_alertes_prix_task",
    bind=True,
    max_retries=1,
    default_retry_delay=600,
)
def detecter_alertes_prix_task(self) -> dict:
    """
    Détecte les variations significatives de prix et crée des AlertePrix.
    Exécuté quotidiennement à 06 h 00 (configuré dans CELERY_BEAT_SCHEDULE).
    """
    if not cache.add(_LOCK_DETECT, "1", _LOCK_TTL):
        logger.info("detecter_alertes_prix_task déjà en cours — ignoré.")
        return {"status": "skipped", "raison": "lock actif"}

    try:
        from baay.services.prix_service import detecter_variations_significatives

        # Fenêtre 7 jours
        alertes_7j = detecter_variations_significatives(periode_jours=7)
        # Fenêtre 30 jours
        alertes_30j = detecter_variations_significatives(periode_jours=30)

        result = {
            "status":       "ok",
            "alertes_7j":   len(alertes_7j),
            "alertes_30j":  len(alertes_30j),
            "total":        len(alertes_7j) + len(alertes_30j),
        }
        logger.info("detecter_alertes_prix_task terminé : %s", result)
        return result

    except Exception as exc:
        logger.exception("detecter_alertes_prix_task erreur : %s", exc)
        raise self.retry(exc=exc)

    finally:
        cache.delete(_LOCK_DETECT)
