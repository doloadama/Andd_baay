"""
Calendrier cultural — pages publiques indexables (SEO, pilier #2).

GET /calendrier-cultural/            — page pilier (toutes cultures)
GET /calendrier-cultural/<slug>/     — fiche par culture (404 si inconnue)

Contenu servi depuis le dataset curé `baay/calendrier_cultural.py` (pas de DB).
"""
from __future__ import annotations

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .calendrier_cultural import (
    MOIS_COURTS,
    get_culture,
    liste_cultures,
    mois_semis_labels,
)


@require_GET
def calendrier_liste(request: HttpRequest) -> HttpResponse:
    context = {
        "cultures": liste_cultures(),
        "seo_title": "Calendrier cultural du Sénégal — semis, cycle & récolte | Andd Baay",
        "seo_description": (
            "Calendrier cultural des principales cultures du Sénégal : quand semer, "
            "cycle, besoin en eau, période de récolte et rendement (mil, arachide, "
            "niébé, sorgho, riz, maïs, tomate, oignon)."
        ),
        "page_h1": "Calendrier cultural du Sénégal",
        "intro_text": (
            "Quand semer, combien de temps dure le cycle, quand récolter : le "
            "calendrier et les bonnes pratiques pour les principales cultures "
            "sénégalaises, en hivernage comme en contre-saison."
        ),
    }
    return render(request, "calendrier/liste.html", context)


@require_GET
def calendrier_detail(request: HttpRequest, slug: str) -> HttpResponse:
    culture = get_culture(slug)
    if culture is None:
        raise Http404("Culture inconnue au calendrier cultural.")

    frise = [
        {"label": MOIS_COURTS[i], "semis": (i + 1) in culture["semis_mois"]}
        for i in range(12)
    ]
    det_de = culture["det_de"]
    context = {
        "culture": culture,
        "frise": frise,
        "semis_label": mois_semis_labels(culture),
        "seo_title": f"Calendrier cultural {det_de} au Sénégal — semis, cycle & récolte | Andd Baay",
        "seo_description": culture["meta_description"],
        "page_h1": f"Calendrier cultural {det_de} au Sénégal",
    }
    return render(request, "calendrier/detail.html", context)
