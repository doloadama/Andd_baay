"""
Tags de gabarit pour graphiques utiles dans l'admin Unfold.
"""

from __future__ import annotations

import json
from decimal import Decimal

from django import template
from django.db.models import Count, Sum

from baay.models import ProjetProduit

register = template.Library()


def _float_or(v, default=0.0) -> float:
    if v is None:
        return default
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


@register.inclusion_tag("admin/partials/yield_compare_chart.html")
def admin_yield_compare_chart(max_points=18):
    """
    Prépare un jeu de données pour comparer, pour chaque ProjetProduit terminé
    (rendement_final renseigné), le rendement réel à la part proportionnelle
    de la prévision IA enregistrée sur le ProjetProduit (PrevisionRecolte).
    """
    max_points = max(4, min(int(max_points), 40))

    base_qs = (
        ProjetProduit.objects.filter(
            rendement_final__gt=0,
            prevision__isnull=False,
        )
        .select_related("projet", "prevision", "produit")
        .order_by("-projet__date_lancement", "produit__nom")
    )

    candidates = list(base_qs[: max_points * 3])
    if not candidates:
        return {
            "has_data": False,
            "chart_json": json.dumps({"labels": [], "reel": [], "prev": []}),
        }

    projet_ids = list({pp.projet_id for pp in candidates})
    sup_rows = (
        ProjetProduit.objects.filter(projet_id__in=projet_ids)
        .values("projet_id")
        .annotate(t=Sum("superficie_allouee"))
    )
    total_superficie_by_projet = {r["projet_id"]: _float_or(r["t"], 0.0) for r in sup_rows}
    cnt_rows = (
        ProjetProduit.objects.filter(projet_id__in=projet_ids)
        .values("projet_id")
        .annotate(c=Count("id"))
    )
    pp_count_by_projet = {r["projet_id"]: r["c"] for r in cnt_rows}

    rows = []
    for pp in candidates:
        prev = pp.prevision
        if not prev:
            continue
        total_sup = total_superficie_by_projet.get(pp.projet_id) or 0.0
        if total_sup <= 0:
            total_sup = _float_or(pp.projet.superficie, 1.0) or 1.0
        pp_sup = _float_or(pp.superficie_allouee, 0.0)
        if pp_sup <= 0:
            n_pp = pp_count_by_projet.get(pp.projet_id) or 1
            pp_sup = total_sup / max(1, n_pp)
        share = min(1.0, max(0.0, pp_sup / total_sup)) if total_sup else 1.0
        prev_mid = (prev.rendement_estime_min + prev.rendement_estime_max) / 2.0
        reel = _float_or(pp.rendement_final, 0.0)
        if reel <= 0:
            continue

        label = f"{pp.projet.nom[:18]}{'…' if len(pp.projet.nom) > 18 else ''} · {pp.produit.nom[:12]}"
        if len(label) > 36:
            label = label[:34] + "…"
        rows.append({"label": label, "reel": round(reel, 2), "prev": round(prev_mid, 2)})

    rows = rows[:max_points]

    if not rows:
        return {
            "has_data": False,
            "chart_json": json.dumps({"labels": [], "reel": [], "prev": []}),
        }

    bundle = {
        "labels": [r["label"] for r in rows],
        "reel": [r["reel"] for r in rows],
        "prev": [r["prev"] for r in rows],
    }
    return {
        "has_data": True,
        "chart_json": json.dumps(bundle),
        "n_points": len(rows),
    }
