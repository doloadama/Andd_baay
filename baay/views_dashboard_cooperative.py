"""
Dashboard coopérative — vue synthèse pour owner gérant N fermes.
Accessible depuis le menu principal pour les propriétaires multi-fermes.
"""
import csv

from django.contrib.auth.decorators import login_required
from django.db.models import Max, OuterRef, Prefetch, Q, Subquery
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import render

from baay.models import (
    AnalyseImageCulture,
    Ferme,
    PrevisionRecolte,
    Projet,
    Tache,
)


@login_required
def dashboard_cooperative(request):
    profile = request.user.profile
    fermes_qs = Ferme.objects.filter(proprietaire=profile).order_by("nom")

    # Optional filter
    ferme_filter = request.GET.get("ferme", "")
    if ferme_filter:
        fermes_qs = fermes_qs.filter(id=ferme_filter)

    fermes = list(fermes_qs)
    ferme_ids = [f.id for f in fermes]

    # Last yield prediction per farm (via projet)
    last_prevision_qs = (
        PrevisionRecolte.objects.filter(projet__ferme=OuterRef("pk"))
        .order_by("-date_prediction")
        .values("rendement_estime_min", "rendement_estime_max", "indice_confiance")[:1]
    )

    fermes_with_data = (
        Ferme.objects.filter(id__in=ferme_ids)
        .annotate(
            last_prevision_min=Subquery(last_prevision_qs.values("rendement_estime_min")),
            last_prevision_max=Subquery(last_prevision_qs.values("rendement_estime_max")),
            last_prevision_confiance=Subquery(last_prevision_qs.values("indice_confiance")),
        )
        .order_by("nom")
    )

    # Last diagnostic per farm
    last_diag_qs = (
        AnalyseImageCulture.objects.filter(
            projet_produit__projet__ferme=OuterRef("pk"),
            statut=AnalyseImageCulture.STATUT_TERMINEE,
        )
        .order_by("-date_creation")
        .values("sujet_description", "date_creation")[:1]
    )
    fermes_with_data = fermes_with_data.annotate(
        last_diag_resume=Subquery(last_diag_qs.values("sujet_description")),
        last_diag_date=Subquery(last_diag_qs.values("date_creation")),
    )

    # Critical tasks per farm (haute/urgente, non terminées)
    critical_tasks = (
        Tache.objects.filter(
            ferme_id__in=ferme_ids,
            priorite__in=["haute", "urgente"],
            statut__in=["a_faire", "en_cours"],
        )
        .values("ferme_id", "titre", "statut", "priorite")
        .order_by("ferme_id", "-priorite")
    )
    tasks_by_ferme: dict = {}
    for t in critical_tasks:
        tasks_by_ferme.setdefault(str(t["ferme_id"]), []).append(t)

    # Active project count per farm
    active_projets = (
        Projet.objects.filter(ferme_id__in=ferme_ids, statut="en_cours")
        .values("ferme_id")
    )
    projets_count: dict = {}
    for p in active_projets:
        projets_count[str(p["ferme_id"])] = projets_count.get(str(p["ferme_id"]), 0) + 1

    # All farms for filter dropdown (unfiltered)
    all_fermes = Ferme.objects.filter(proprietaire=profile).order_by("nom").values("id", "nom")

    # ── CSV export ──────────────────────────────────────────────────────────
    if request.GET.get("export") == "csv":
        return _export_csv(fermes_with_data, tasks_by_ferme)

    rows = []
    for ferme in fermes_with_data:
        fid = str(ferme.id)
        taches = tasks_by_ferme.get(fid, [])
        rows.append({
            "ferme": ferme,
            "prevision_min": ferme.last_prevision_min,
            "prevision_max": ferme.last_prevision_max,
            "prevision_confiance": ferme.last_prevision_confiance,
            "diag_resume": ferme.last_diag_resume,
            "diag_date": ferme.last_diag_date,
            "taches_critiques": taches,
            "projets_actifs": projets_count.get(fid, 0),
            "needs_attention": bool(taches),
        })

    # ── Agrégats pour la bande KPI ──────────────────────────────────────────
    summary = {
        "total_fermes": len(rows),
        "projets_actifs": sum(r["projets_actifs"] for r in rows),
        "taches_critiques": sum(len(r["taches_critiques"]) for r in rows),
        "fermes_attention": sum(1 for r in rows if r["needs_attention"]),
        "fermes_prevision": sum(1 for r in rows if r["prevision_min"] is not None),
    }

    return render(request, "dashboard/cooperative.html", {
        "rows": rows,
        "all_fermes": all_fermes,
        "ferme_filter": ferme_filter,
        "total_fermes": len(fermes),
        "summary": summary,
    })


def _export_csv(fermes_with_data, tasks_by_ferme):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="cooperative_export.csv"'
    response.write("﻿")  # BOM for Excel

    writer = csv.writer(response)
    writer.writerow([
        "Ferme", "Rendement estimé min (kg/ha)", "Rendement estimé max (kg/ha)",
        "Confiance (%)", "Dernier diagnostic", "Date diagnostic",
        "Tâches critiques en cours",
    ])
    for ferme in fermes_with_data:
        fid = str(ferme.id)
        critical = tasks_by_ferme.get(fid, [])
        writer.writerow([
            ferme.nom,
            ferme.last_prevision_min or "",
            ferme.last_prevision_max or "",
            ferme.last_prevision_confiance or "",
            (ferme.last_diag_resume or "")[:100],
            ferme.last_diag_date.strftime("%d/%m/%Y %H:%M") if ferme.last_diag_date else "",
            len(critical),
        ])
    return response
