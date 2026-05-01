"""
Données agrégées pour le tableau de bord Unfold (admin index).
Requêtes groupées / annotate pour éviter le N+1 et limiter le nombre de hits DB.
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone


def dashboard_callback(request, context: dict[str, Any]) -> dict[str, Any]:
    from baay.models import DemandeAccesFerme, Ferme, Investissement, Message, Projet, Tache

    User = get_user_model()
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    six_m_ago = month_start - timedelta(days=180)

    demandes_aggr = DemandeAccesFerme.objects.aggregate(
        pending=Count("id", filter=Q(statut="en_attente")),
    )

    projets_agg = Projet.objects.aggregate(
        total=Count("id"),
        en_cours=Count("id", filter=Q(statut="en_cours")),
    )

    taches_agg = Tache.objects.filter(statut__in=("a_faire", "en_cours")).aggregate(
        ouvertes=Count("id"),
        retard=Count("id", filter=Q(date_echeance__lt=now.date())),
    )

    counts = {
        "fermes": Ferme.objects.count(),
        "projets": projets_agg["total"] or 0,
        "projets_en_cours": projets_agg["en_cours"] or 0,
        "messages": Message.objects.count(),
        "investissements": Investissement.objects.count(),
        "demandes_pending": demandes_aggr["pending"] or 0,
        "taches_ouvertes": taches_agg["ouvertes"] or 0,
        "taches_retard": taches_agg["retard"] or 0,
    }

    active_users_logged = User.objects.filter(last_login__gte=month_start).count()

    monthly = list(
        Projet.objects.filter(date_lancement__gte=six_m_ago.date())
        .annotate(month=TruncMonth("date_lancement"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    chart_labels = []
    chart_values = []
    for row in monthly:
        m = row["month"]
        if m is None:
            continue
        chart_labels.append(m.strftime("%b %Y"))
        chart_values.append(row["total"])

    warnings = []
    if counts["taches_retard"] > 0:
        warnings.append(
            {
                "text": (
                    f"{counts['taches_retard']} tâche(s) en retard "
                    "(échéance dépassée, non terminées)."
                )
            },
        )
    if counts["demandes_pending"] > 0:
        warnings.append(
            {
                "text": (
                    f"{counts['demandes_pending']} demande(s) d'accès ferme "
                    "en attente de traitement."
                )
            },
        )

    chart_bundle = {"labels": chart_labels, "values": chart_values}

    context.update(
        {
            "dashboard_kpis": [
                {
                    "label": "Fermes",
                    "value": counts["fermes"],
                    "hint": "Exploitations enregistrées",
                    "icon": "agriculture",
                },
                {
                    "label": "Projets",
                    "value": counts["projets"],
                    "hint": "Tous statuts confondus",
                    "icon": "eco",
                },
                {
                    "label": "Projets actifs",
                    "value": counts["projets_en_cours"],
                    "hint": "Statut « en cours »",
                    "icon": "trending_up",
                },
                {
                    "label": "Investissements",
                    "value": counts["investissements"],
                    "hint": "Lignes enregistrées",
                    "icon": "payments",
                },
                {
                    "label": "Demandes d'accès",
                    "value": counts["demandes_pending"],
                    "hint": "En attente de validation",
                    "icon": "mark_email_unread",
                },
                {
                    "label": "Tâches ouvertes",
                    "value": counts["taches_ouvertes"],
                    "hint": "À faire + en cours",
                    "icon": "assignment",
                },
                {
                    "label": "Messages",
                    "value": counts["messages"],
                    "hint": "Messagerie interne",
                    "icon": "chat",
                },
                {
                    "label": "Connexions (mois)",
                    "value": active_users_logged,
                    "hint": "Utilisateurs avec last_login récent",
                    "icon": "people",
                },
            ],
            "dashboard_chart_json": json.dumps(chart_bundle),
            "dashboard_warnings": warnings,
        },
    )

    return context
