from __future__ import annotations

import logging
from typing import Iterable, Sequence

from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from .models import Projet, ProjetProduit, MembreFerme, Ferme, Profile

logger = logging.getLogger(__name__)
from .services import (
    compute_previsions_for_projet,
    check_budget_status,
    check_projet_produit_budget_status,
)
from .services.prediction_accuracy import invalider_cache_correcteurs_biais


def _recipient_profile_ids_for_ferme(ferme: Ferme) -> Sequence[int]:
    qs = Profile.objects.filter(
        id__in=list(
            set(
                [ferme.proprietaire_id]
                + list(MembreFerme.objects.filter(ferme=ferme).values_list("utilisateur_id", flat=True))
            )
        )
    ).values_list("id", flat=True)
    return list(qs)


@shared_task(bind=True, ignore_result=False)
def generate_previsions_for_projet_task(self, projet_id: str) -> dict:
    """Compute PrevisionRecolte for each ProjetProduit and update Projet.rendement_estime.

    Emits a Channels event (task_update_v1) to each ferme member's inbox group when done.
    """
    summary = compute_previsions_for_projet(projet_id)
    projet = summary["projet"]
    total_min = summary["total_min"]
    total_max = summary["total_max"]

    # Notify via Channels
    layer = get_channel_layer()
    recipients = _recipient_profile_ids_for_ferme(projet.ferme)
    payload = {
        "type": "task_update_v1",
        "event_version": "v1",
        "task": "prevision_recolte",
        "status": "completed",
        "projet_id": str(projet.id),
        "projet_nom": projet.nom,
        "rendement_estime": projet.rendement_estime,
        "rendement_min_total": total_min,
        "rendement_max_total": total_max,
    }
    for pid in recipients:
        try:
            async_to_sync(layer.group_send)(f"inbox_{pid}", payload)
        except Exception as exc:
            logger.warning("Channels broadcast failed for inbox_%s: %s", pid, exc)

    return {
        "ok": True,
        "projet_id": str(projet.id),
        "rendement_estime": projet.rendement_estime,
        "rendement_min_total": total_min,
        "rendement_max_total": total_max,
        "count_pp": summary["count_pp"],
    }


@shared_task(bind=True, ignore_result=True)
def recompute_investment_budget_status_task(self, projet_id: str) -> None:
    """Recompute budget status for a projet and emit a milestone update if over budget."""
    projet = Projet.objects.select_related("ferme").get(pk=projet_id)
    status = check_budget_status(projet_id)
    over = bool(status.get("applicable") and status.get("over_budget"))
    # Also check any culture-level overruns
    if not over:
        for pp_id in ProjetProduit.objects.filter(projet=projet).values_list("id", flat=True):
            stp = check_projet_produit_budget_status(str(pp_id))
            if stp.get("applicable") and stp.get("over_budget"):
                over = True
                break

    if over:
        layer = get_channel_layer()
        recipients = _recipient_profile_ids_for_ferme(projet.ferme)
        payload = {
            "type": "milestone_update_v1",
            "event_version": "v1",
            "milestone": "budget_overrun",
            "projet_id": str(projet.id),
            "projet_nom": projet.nom,
        }
        for pid in recipients:
            try:
                async_to_sync(layer.group_send)(f"inbox_{pid}", payload)
            except Exception as exc:
                logger.warning("Channels broadcast failed for inbox_%s: %s", pid, exc)


@shared_task(bind=True, ignore_result=True)
def refresher_correcteurs_biais_task(self) -> None:
    """Invalide le cache Redis des correcteurs de biais et le recharge immédiatement.

    Planifié toutes les 6h via Celery Beat pour intégrer les nouvelles clôtures
    de projets sans attendre l'expiration naturelle du cache (24h).
    """
    invalider_cache_correcteurs_biais()
    # Déclenche immédiatement le recalcul pour pré-chauffer le cache
    from .services.prediction_accuracy import get_correcteurs_biais_par_culture
    try:
        correcteurs = get_correcteurs_biais_par_culture()
        logger.info(
            "Correcteurs de biais rafraichis : %d cultures calibrees.", len(correcteurs)
        )
    except Exception as exc:
        logger.warning("Impossible de recharger les correcteurs de biais : %s", exc)


@shared_task(bind=True, ignore_result=True)
def recompute_active_predictions_task(self) -> None:
    """Recalcule toutes les PrevisionRecolte des projets actifs.

    Planifié chaque nuit (2h00) afin que la progression phénologique (P2.1)
    réduise progressivement la variance et augmente la confiance au fil du cycle.
    Seuls les ProjetProduit avec date_semis définie et projet en cours sont traités.
    """
    from .services import update_prediction_for_projet_produit

    qs = (
        ProjetProduit.objects.filter(
            projet__statut='en_cours',
            date_semis__isnull=False,
        )
        .select_related('produit', 'projet', 'projet__localite', 'projet__ferme')
    )

    total = 0
    errors = 0
    for pp in qs.iterator(chunk_size=200):
        try:
            update_prediction_for_projet_produit(pp)
            total += 1
        except Exception as exc:
            errors += 1
            logger.warning(
                "Erreur recalcul prediction ProjetProduit %s : %s", pp.pk, exc
            )

    logger.info(
        "recompute_active_predictions : %d recalcules, %d erreurs.", total, errors
    )


@shared_task(bind=True, ignore_result=True, name="baay.tasks.auto_retrain_models_task")
def auto_retrain_models_task(
    self,
    declencheur: str = "auto",
    min_new_obs: int = 5,
    min_n: int = 5,
) -> None:
    """Réentraîne en warm-start les modèles XGBoost pour les cultures avec de nouvelles données.

    Appelé :
      - Chaque dimanche à 3h00 (Celery Beat) avec declencheur='auto'.
      - Sur signal post-clôture quand une culture atteint MIN_NEW_OBS_AUTO nouvelles
        observations (declencheur='signal').
      - Manuellement via ``python manage.py entrainer_modele_ml`` (declencheur='manuel').

    Stratégie warm-start :
      Ajoute 50 arbres au booster existant au lieu de tout réapprendre (200 arbres).
      Préserve la mémoire des données historiques tout en s'adaptant aux nouvelles.

    Post-entraînement :
      - Invalide le cache des correcteurs de biais.
      - Déclenche recompute_active_predictions_task pour appliquer les nouveaux modèles.
    """
    from .services.ml_training import cultures_a_reentrainer, entrainer_culture
    from .services.prediction_accuracy import (
        get_correcteurs_biais_par_culture,
        invalider_cache_correcteurs_biais,
    )

    cultures = cultures_a_reentrainer(min_new_obs=min_new_obs)
    if not cultures:
        logger.info(
            "auto_retrain_models [%s] : aucune culture avec >= %d nouvelles observations.",
            declencheur, min_new_obs,
        )
        return

    logger.info(
        "auto_retrain_models [%s] : %d culture(s) à ré-entraîner : %s",
        declencheur, len(cultures), cultures,
    )

    retrained = []
    for culture_nom in cultures:
        try:
            result = entrainer_culture(
                culture_nom,
                min_n=min_n,
                warm_start=True,
                declencheur=declencheur,
            )
            if result:
                retrained.append(result)
                logger.info(
                    "auto_retrain [%s] R2=%.3f RMSE=%.0f kg improved=%s ws=%s",
                    culture_nom,
                    result["r2"],
                    result["rmse"],
                    result["improved"],
                    result["warm_start_used"],
                )
        except Exception as exc:
            logger.error(
                "auto_retrain_models [%s] erreur : %s", culture_nom, exc, exc_info=True
            )

    if retrained:
        # Recalibrer les correcteurs de biais avec les nouvelles données
        invalider_cache_correcteurs_biais()
        try:
            get_correcteurs_biais_par_culture()
        except Exception as exc:
            logger.warning("Rechargement correcteurs de biais : %s", exc)

        # Appliquer immédiatement les nouveaux modèles aux projets actifs
        recompute_active_predictions_task.delay()

    logger.info(
        "auto_retrain_models : terminé — %d/%d modèle(s) mis à jour.",
        sum(1 for r in retrained if r["improved"]),
        len(retrained),
    )
