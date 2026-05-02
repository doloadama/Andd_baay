"""
Agrégations pour le tableau de bord admin Unfold (périmètre ferme / rôle).

Les requêtes utilisent des QuerySet filtrés selon `fermes_accessibles_qs` /
`projets_accessibles_qs`, sauf pour le superutilisateur (vue plateforme).
"""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db.models import (
    Avg,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Min,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from baay import permissions as perm
from baay.models import (
    Ferme,
    Investissement,
    PrevisionRecolte,
    Projet,
    ProjetProduit,
    Profile,
    Tache,
)

THEME = {
    "forest": "#1D9E75",
    "earth": "#EF9F27",
    "deep": "#085041",
    "forestSoft": "rgba(29, 158, 117, 0.35)",
    "earthSoft": "rgba(239, 159, 39, 0.35)",
}


def _fdec(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


def resolve_scope(request) -> dict[str, Any]:
    """
    Retourne profile, fermes_qs, projets_qs, is_global, scope_label.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {
            "profile": None,
            "fermes_qs": Ferme.objects.none(),
            "projets_qs": Projet.objects.none(),
            "is_global": False,
            "scope_label": "Non connecté",
        }

    if user.is_superuser:
        return {
            "profile": getattr(user, "profile", None),
            "fermes_qs": Ferme.objects.all(),
            "projets_qs": Projet.objects.all(),
            "is_global": True,
            "scope_label": "Vue plateforme (superutilisateur)",
        }

    try:
        profile = user.profile
    except Profile.DoesNotExist:
        return {
            "profile": None,
            "fermes_qs": Ferme.objects.none(),
            "projets_qs": Projet.objects.none(),
            "is_global": False,
            "scope_label": "Aucun profil Baay — périmètre vide",
        }

    fermes_qs = perm.fermes_accessibles_qs(profile)
    projets_qs = perm.projets_accessibles_qs(profile)
    return {
        "profile": profile,
        "fermes_qs": fermes_qs,
        "projets_qs": projets_qs,
        "is_global": False,
        "scope_label": "Vos fermes et rattachements (MembreFerme)",
    }


def effective_roles_for_profile(profile: Profile | None, fermes_qs) -> set[str]:
    """Rôles sur le périmètre (hors ouvrier pour les couches métier)."""
    if profile is None:
        return set()
    roles: set[str] = set()
    for ferme in fermes_qs.only("id", "proprietaire_id"):
        r = perm.role_dans_ferme(profile, ferme)
        if r and r != perm.ROLE_OUVRIER:
            roles.add(r)
    return roles


def layer_visible_flags(is_global: bool, roles: set[str]) -> dict[str, bool]:
    if is_global:
        return {"owner": True, "manager": True, "technicien": True}
    return {
        "owner": perm.ROLE_PROPRIETAIRE in roles,
        "manager": perm.ROLE_MANAGER in roles,
        "technicien": perm.ROLE_TECHNICIEN in roles,
    }


def _inv_line_expr():
    return ExpressionWrapper(
        F("cout_par_hectare") * F("projet__superficie")
        + Coalesce(
            F("autres_frais"),
            Value(Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=4)),
        ),
        output_field=DecimalField(max_digits=28, decimal_places=8),
    )


def aggregate_platform_kpis(fermes_qs, projets_qs, now) -> dict[str, int]:
    """Compteurs pour les cartes KPI (filtrés par périmètre ferme / projet)."""
    from baay.models import DemandeAccesFerme, Message

    demandes_aggr = DemandeAccesFerme.objects.filter(ferme__in=fermes_qs).aggregate(
        pending=Count("id", filter=Q(statut="en_attente")),
    )
    projets_agg = projets_qs.aggregate(
        total=Count("id"),
        en_cours=Count("id", filter=Q(statut="en_cours")),
    )
    taches_agg = (
        Tache.objects.filter(ferme__in=fermes_qs)
        .filter(statut__in=("a_faire", "en_cours"))
        .aggregate(
            ouvertes=Count("id"),
            retard=Count("id", filter=Q(date_echeance__lt=now.date())),
        )
    )
    # Messages rattachés aux conversations d'une ferme du périmètre
    msg_qs = Message.objects.filter(conversation__ferme__in=fermes_qs)
    if not fermes_qs.exists():
        msg_count = 0
    else:
        msg_count = msg_qs.count()

    return {
        "fermes": fermes_qs.count(),
        "projets": projets_agg["total"] or 0,
        "projets_en_cours": projets_agg["en_cours"] or 0,
        "messages": msg_count,
        "investissements": Investissement.objects.filter(projet__in=projets_qs).count(),
        "demandes_pending": demandes_aggr["pending"] or 0,
        "taches_ouvertes": taches_agg["ouvertes"] or 0,
        "taches_retard": taches_agg["retard"] or 0,
    }


def build_owner_payload(fermes_qs, projets_qs) -> dict[str, Any]:
    """Propriétaire : ROI, cultures, perf inter-fermes, cash-flow."""
    inv_line = _inv_line_expr()
    inv_total_row = Investissement.objects.filter(projet__in=projets_qs).aggregate(
        total=Sum(inv_line)
    )
    total_inv = _fdec(inv_total_row["total"])

    rev_expr = ExpressionWrapper(
        Coalesce(
            F("rendement_final"),
            Value(Decimal("0"), output_field=DecimalField(max_digits=14, decimal_places=4)),
        )
        * Coalesce(
            F("produit__prix_par_kg"),
            Value(Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=4)),
        ),
        output_field=DecimalField(max_digits=24, decimal_places=8),
    )
    rev_row = ProjetProduit.objects.filter(projet__in=projets_qs).aggregate(rev=Sum(rev_expr))
    total_rev = _fdec(rev_row["rev"])

    if total_inv > 0:
        roi_pct = (total_rev - total_inv) / total_inv * 100.0
    else:
        roi_pct = 0.0
    roi_gauge = max(-100.0, min(200.0, roi_pct))

    culture_rows = list(
        ProjetProduit.objects.filter(projet__in=projets_qs)
        .values("produit__nom")
        .annotate(
            ha=Sum(
                Coalesce(
                    F("superficie_allouee"),
                    Value(Decimal("0"), output_field=DecimalField(max_digits=14, decimal_places=4)),
                )
            )
        )
        .order_by("-ha")[:12]
    )
    donut_labels = [r["produit__nom"] or "—" for r in culture_rows]
    donut_series = [_fdec(r["ha"]) for r in culture_rows]

    ferme_rows = list(
        Investissement.objects.filter(projet__ferme__in=fermes_qs)
        .values("projet__ferme__nom")
        .annotate(montant=Sum(inv_line))
        .order_by("-montant")[:10]
    )
    ferme_cats = [r["projet__ferme__nom"] or "—" for r in ferme_rows]
    ferme_inv = [_fdec(r["montant"]) for r in ferme_rows]

    today = timezone.now().date()
    start = today - timedelta(days=365)
    cash_rows = list(
        Investissement.objects.filter(projet__in=projets_qs, date_investissement__gte=start)
        .annotate(m=TruncMonth("date_investissement"))
        .values("m")
        .annotate(s=Sum(inv_line))
        .order_by("m")
    )
    cash_labels = []
    cash_values = []
    for row in cash_rows:
        m = row["m"]
        if m is None:
            continue
        cash_labels.append(m.strftime("%b %Y"))
        cash_values.append(_fdec(row["s"]))

    return {
        "roi_gauge": round(roi_gauge, 1),
        "roi_pct_raw": round(roi_pct, 1),
        "total_invest": round(total_inv, 2),
        "total_revenue_proxy": round(total_rev, 2),
        "cultures_donut": {"labels": donut_labels, "series": donut_series},
        "fermes_bar": {"categories": ferme_cats, "data": ferme_inv},
        "cashflow_area": {"labels": cash_labels, "values": cash_values},
    }


def build_manager_payload(fermes_qs, projets_qs) -> dict[str, Any]:
    """Manager : complétion tâches, budget (répartition), charge par membre."""
    inv_line = _inv_line_expr()
    taches = Tache.objects.filter(ferme__in=fermes_qs).exclude(statut="annulee")
    t_agg = taches.aggregate(
        total=Count("id"),
        done=Count("id", filter=Q(statut="terminee")),
    )
    total_t = t_agg["total"] or 0
    done_t = t_agg["done"] or 0
    completion_pct = (done_t / total_t * 100.0) if total_t else 0.0

    inv_total = Investissement.objects.filter(projet__in=projets_qs).aggregate(t=Sum(inv_line))
    total_inv = _fdec(inv_total["t"])
    proj_rows = list(
        Investissement.objects.filter(projet__in=projets_qs)
        .values("projet__nom")
        .annotate(montant=Sum(inv_line))
        .order_by("-montant")[:10]
    )
    budget_labels = [r["projet__nom"] or "—" for r in proj_rows]
    budget_series = [_fdec(r["montant"]) for r in proj_rows]

    workload = list(
        Tache.objects.filter(ferme__in=fermes_qs, statut__in=("a_faire", "en_cours"))
        .values("assigne_a__user__username")
        .annotate(n=Count("id"))
        .order_by("-n")[:12]
    )
    workload_labels = [r["assigne_a__user__username"] or "—" for r in workload]
    workload_counts = [r["n"] for r in workload]

    return {
        "task_completion_pct": round(completion_pct, 1),
        "task_open": taches.filter(statut__in=("a_faire", "en_cours")).count(),
        "task_done": done_t,
        "task_total_non_cancel": total_t,
        "invest_total": round(total_inv, 2),
        "budget_donut": {"labels": budget_labels, "series": budget_series},
        "workload_radial": {
            "labels": workload_labels,
            "series": workload_counts,
        },
    }


def build_technicien_payload(fermes_qs, projets_qs) -> dict[str, Any]:
    """Technicien : écart ML, countdown récolte, alertes tâches critiques."""
    today = timezone.now().date()
    pp_qs = ProjetProduit.objects.filter(
        projet__in=projets_qs,
        prevision__isnull=False,
        rendement_final__isnull=False,
        rendement_final__gt=0,
    ).select_related("projet", "produit", "prevision")

    scatter: list[dict[str, Any]] = []
    for pp in pp_qs[:40]:
        prev = pp.prevision
        if not prev:
            continue
        prev_mid = (float(prev.rendement_estime_min) + float(prev.rendement_estime_max)) / 2.0
        reel = _fdec(pp.rendement_final)
        label = f"{pp.projet.nom[:14]} · {pp.produit.nom[:10]}"
        scatter.append(
            {
                "x": round(prev_mid, 2),
                "y": round(reel, 2),
                "label": label,
            }
        )

    next_recolte = ProjetProduit.objects.filter(
        projet__in=projets_qs,
        date_recolte_prevue__gte=today,
    ).aggregate(d=Min("date_recolte_prevue"))
    dmin = next_recolte["d"]
    countdown_days = None
    if dmin:
        countdown_days = (dmin - today).days

    alerts = Tache.objects.filter(
        ferme__in=fermes_qs,
        priorite__in=("haute", "urgente"),
        statut__in=("a_faire", "en_cours"),
        date_echeance__lt=today,
    ).count()

    return {
        "scatter_ml": scatter,
        "countdown_days": countdown_days,
        "next_recolte": dmin.isoformat() if dmin else None,
        "critical_overdue_tasks": alerts,
    }


def prevision_summary(projets_qs) -> dict[str, Any]:
    prev_agg = PrevisionRecolte.objects.filter(projet__in=projets_qs).aggregate(
        avec_prev=Count("id"),
        confiance_moy=Avg("indice_confiance"),
        rend_min_moy=Avg("rendement_estime_min"),
        rend_max_moy=Avg("rendement_estime_max"),
    )
    projets_total = projets_qs.count()
    projets_avec_prev = (
        PrevisionRecolte.objects.filter(projet__in=projets_qs).values("projet_id").distinct().count()
    )
    return {
        "nb_prev": prev_agg["avec_prev"] or 0,
        "confiance_moy": round(_fdec(prev_agg["confiance_moy"]), 1),
        "rend_min_moy": round(_fdec(prev_agg["rend_min_moy"]), 2),
        "rend_max_moy": round(_fdec(prev_agg["rend_max_moy"]), 2),
        "projets_sans_prev": max(0, projets_total - projets_avec_prev),
    }


def invest_par_projet_table(projets_qs, limit: int = 16) -> list[dict[str, Any]]:
    inv_line = _inv_line_expr()
    return list(
        Investissement.objects.filter(projet__in=projets_qs)
        .values("projet_id", "projet__nom")
        .annotate(montant_total=Sum(inv_line), nb_lignes=Count("id"))
        .order_by("-montant_total")[:limit]
    )


def monthly_new_projects(projets_qs, now) -> tuple[list[str], list[int]]:
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    six_m_ago = month_start - timedelta(days=180)
    monthly = list(
        projets_qs.filter(date_lancement__gte=six_m_ago.date())
        .annotate(month=TruncMonth("date_lancement"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    labels, values = [], []
    for row in monthly:
        m = row["month"]
        if m is None:
            continue
        labels.append(m.strftime("%b %Y"))
        values.append(row["total"])
    return labels, values


def build_apex_payload(
    layers: dict[str, bool],
    owner: dict[str, Any],
    manager: dict[str, Any],
    technicien: dict[str, Any],
) -> dict[str, Any]:
    """Structure unique consommée par le gabarit (ApexCharts)."""
    return {
        "theme": THEME,
        "layers": layers,
        "owner": owner,
        "manager": manager,
        "technicien": technicien,
    }


def apex_payload_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def changelist_dashboard_hint(request, slug: str) -> dict[str, Any]:
    """Données légères pour la bannière sous list_before (injection ModelAdmin)."""
    scope = resolve_scope(request)
    fermes_qs = scope["fermes_qs"]
    projets_qs = scope["projets_qs"]
    kpis = aggregate_platform_kpis(fermes_qs, projets_qs, timezone.now())
    hints = {
        "ferme": {
            "title": "Tableau de bord — périmètre fermes",
            "body": f"{kpis['fermes']} ferme(s) · {kpis['projets']} projet(s) visibles.",
        },
        "projet": {
            "title": "Projets et cultures",
            "body": f"{kpis['projets_en_cours']} en cours · investissements : {kpis['investissements']} ligne(s).",
        },
        "investissement": {
            "title": "Budget & investissements",
            "body": "Graphiques cash-flow et répartition sur l’accueil admin.",
        },
        "tache": {
            "title": "Tâches",
            "body": f"{kpis['taches_ouvertes']} ouverte(s) · {kpis['taches_retard']} en retard.",
        },
        "previsionrecolte": {
            "title": "Prévisions IA",
            "body": "Précision réel vs ML sur la section Technicien du tableau de bord.",
        },
    }
    return hints.get(
        slug,
        {
            "title": "Tableau de bord",
            "body": "Vue consolidée sur la page d’accueil de l’administration.",
        },
    )


class DashboardChangelistMixin:
    """
    Mixin Unfold : injecte un court rappel + lien vers l’accueil (équivalent
    « dashboard_callback » par modèle — Unfold n’expose pas ce hook sur ModelAdmin).
    """

    baay_dashboard_slug: str = ""

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        slug = getattr(self, "baay_dashboard_slug", None) or getattr(
            self.model._meta, "model_name", ""
        )
        extra_context["baay_changelist_dashboard"] = changelist_dashboard_hint(request, slug)
        return super().changelist_view(request, extra_context)
