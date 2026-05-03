from __future__ import annotations

from typing import Iterable, Sequence

from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from .models import Projet, ProjetProduit, MembreFerme, Ferme, Profile
from .services import (
    compute_previsions_for_projet,
    check_budget_status,
    check_projet_produit_budget_status,
)


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
        async_to_sync(layer.group_send)(f"inbox_{pid}", payload)

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
            async_to_sync(layer.group_send)(f"inbox_{pid}", payload)
