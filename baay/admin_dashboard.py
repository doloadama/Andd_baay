"""
Données agrégées pour le tableau de bord Unfold (admin index).

Délègue les calculs rôle / périmètre à `baay.dashboard_services`.
"""

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth import get_user_model
from django.utils import timezone

from baay import dashboard_services as dash


def dashboard_callback(request, context: dict[str, Any]) -> dict[str, Any]:
    now = timezone.now()
    scope = dash.resolve_scope(request)
    fermes_qs = scope["fermes_qs"]
    projets_qs = scope["projets_qs"]
    profile = scope["profile"]
    is_global = scope["is_global"]

    User = get_user_model()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    counts = dash.aggregate_platform_kpis(fermes_qs, projets_qs, now)

    active_users_logged = User.objects.filter(last_login__gte=month_start).count()

    chart_labels, chart_values = dash.monthly_new_projects(projets_qs, now)
    chart_bundle = {"labels": chart_labels, "values": chart_values}

    warnings = []
    if counts["taches_retard"] > 0:
        warnings.append(
            {
                "text": (
                    f"{counts['taches_retard']} tâche(s) en retard "
                    "(échéance dépassée, non terminées)."
                ),
            },
        )
    if counts["demandes_pending"] > 0:
        warnings.append(
            {
                "text": (
                    f"{counts['demandes_pending']} demande(s) d'accès ferme "
                    "en attente de traitement."
                ),
            },
        )

    if is_global:
        roles = set()
    else:
        roles = dash.effective_roles_for_profile(profile, fermes_qs)
    layers = dash.layer_visible_flags(is_global, roles)
    ouvrier_only = (
        not is_global
        and profile is not None
        and fermes_qs.exists()
        and len(roles) == 0
    )

    owner_data = dash.build_owner_payload(fermes_qs, projets_qs)
    manager_data = dash.build_manager_payload(fermes_qs, projets_qs)
    technicien_data = dash.build_technicien_payload(fermes_qs, projets_qs)
    prev_block = dash.prevision_summary(projets_qs)
    invest_par_projet = dash.invest_par_projet_table(projets_qs, limit=16)

    apex_payload = dash.build_apex_payload(
        layers,
        owner_data,
        manager_data,
        technicien_data,
    )

    context.update(
        {
            "dashboard_scope_label": scope["scope_label"],
            "dashboard_layers": layers,
            "dashboard_ouvrier_only": ouvrier_only,
            "dashboard_kpis": [
                {
                    "label": "Fermes",
                    "value": counts["fermes"],
                    "hint": scope["scope_label"],
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
                    "hint": "Messagerie (fermes du périmètre)",
                    "icon": "chat",
                },
                {
                    "label": "Connexions (mois)",
                    "value": active_users_logged,
                    "hint": "Utilisateurs avec last_login récent",
                    "icon": "people",
                },
            ],
            "dashboard_prevision": prev_block,
            "dashboard_invest_par_projet": invest_par_projet,
            "dashboard_chart_json": json.dumps(chart_bundle),
            "dashboard_warnings": warnings,
            "dashboard_apex_json": dash.apex_payload_json(apex_payload),
        },
    )

    return context
