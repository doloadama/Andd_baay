# baay/views_actualites.py
"""
Vues pour la page Actualités agro-météo.

GET  /actualites/                  — liste paginée (30/page)
GET  /actualites/?source=anacim    — filtre par source
GET  /actualites/?categorie=meteo  — filtre par catégorie
GET  /actualites/rafraichir/       — déclenchement manuel de fetch (owner/admin only)
"""
from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import ArticleActualite

logger = logging.getLogger(__name__)

_PAGE_SIZE = 24

# Métadonnées SEO par catégorie (clé "" = page principale "toutes catégories").
# Pages-hub indexables ciblant des requêtes francophones Sénégal/Sahel.
_ACTU_SEO = {
    "": {
        "title": "Actualités agricoles & météo au Sénégal | Andd Baay",
        "description": (
            "Actualité agro-météo du Sénégal : alertes météo, conseils agricoles, "
            "marchés et prix, politique agricole. Sources officielles ANACIM, "
            "Ministère de l'Agriculture, FAO — mis à jour en continu."
        ),
        "h1": "Actualités agro-météo du Sénégal",
        "intro": (
            "Toute l'actualité agricole et météorologique du Sénégal, agrégée depuis "
            "les sources officielles et mise à jour en continu."
        ),
    },
    "meteo": {
        "title": "Actualités météo agricole au Sénégal | Andd Baay",
        "description": (
            "Prévisions et alertes météo pour l'agriculture sénégalaise : pluies, "
            "sécheresse, agroclimat. Sources ANACIM et partenaires."
        ),
        "h1": "Météo & agroclimat au Sénégal",
        "intro": (
            "Prévisions, alertes et bulletins agroclimatiques qui impactent vos "
            "cultures au Sénégal."
        ),
    },
    "conseil": {
        "title": "Conseils agricoles au Sénégal — Actualités | Andd Baay",
        "description": (
            "Conseils agricoles pour le Sénégal : itinéraires techniques, gestion "
            "des cultures, bonnes pratiques. Sources officielles agro."
        ),
        "h1": "Conseils agricoles au Sénégal",
        "intro": "Recommandations et bonnes pratiques pour réussir vos campagnes agricoles.",
    },
    "marche": {
        "title": "Marchés & prix agricoles au Sénégal — Actualités | Andd Baay",
        "description": (
            "Actualité des marchés et des prix agricoles au Sénégal : mil, arachide, "
            "riz, maïs, oignon. Tendances et relevés des marchés."
        ),
        "h1": "Marchés & prix agricoles au Sénégal",
        "intro": "Suivez les tendances des marchés et l'évolution des prix agricoles.",
    },
    "politique": {
        "title": "Politique agricole au Sénégal — Actualités | Andd Baay",
        "description": (
            "Actualité de la politique agricole sénégalaise : programmes, subventions, "
            "campagnes et mesures du secteur agricole."
        ),
        "h1": "Politique agricole au Sénégal",
        "intro": "Décisions, programmes et mesures qui façonnent l'agriculture sénégalaise.",
    },
    "autre": {
        "title": "Actualités agricoles au Sénégal | Andd Baay",
        "description": "Autres actualités agricoles et rurales du Sénégal.",
        "h1": "Autres actualités agricoles",
        "intro": "Autres actualités du secteur agricole et rural au Sénégal.",
    },
}


@require_GET
def liste_actualites(request: HttpRequest, categorie: str | None = None) -> HttpResponse:
    """
    Page publique des actualités agro-météo (indexable SEO).

    - /actualites/                 → toutes catégories
    - /actualites/<categorie>/     → page-hub par catégorie (404 si inconnue)
    - ?source= / ?categorie= / ?page=  → filtres UX (canonical = chemin propre)
    """
    source = request.GET.get("source", "").strip()
    cat_query = request.GET.get("categorie", "").strip()

    valides = dict(ArticleActualite.CATEGORIE_CHOICES)
    if categorie is not None:
        # Catégorie de chemin (page-hub indexable) : 404 si inconnue.
        if categorie not in valides:
            raise Http404("Catégorie d'actualité inconnue.")
        cat_actif = categorie
    else:
        cat_actif = cat_query if cat_query in valides else ""

    qs = ArticleActualite.objects.filter(actif=True)
    if source and source in dict(ArticleActualite.SOURCE_CHOICES):
        qs = qs.filter(source=source)
    if cat_actif:
        qs = qs.filter(categorie=cat_actif)

    paginator = Paginator(qs, _PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    meta = _ACTU_SEO.get(cat_actif, _ACTU_SEO[""])
    context = {
        "page_obj":        page_obj,
        "source_actif":    source,
        "categorie_actif": cat_actif,
        "sources":         ArticleActualite.SOURCE_CHOICES,
        "categories":      ArticleActualite.CATEGORIE_CHOICES,
        "total":           qs.count(),
        # SEO
        "seo_title":       meta["title"],
        "seo_description": meta["description"],
        "page_h1":         meta["h1"],
        "intro_text":      meta["intro"],
    }
    return render(request, "actualites/liste.html", context)


@login_required
@require_GET
def bandeau_alertes_prix(request: HttpRequest) -> HttpResponse:
    """
    Fragment HTMX : bandeau d'alertes prix pour la page Actualités.
    Retourne un div vide (masqué) si aucune alerte récente.
    """
    from baay.models import AlertePrix
    from django.utils.timezone import now
    from datetime import timedelta

    alertes = list(
        AlertePrix.objects
        .filter(
            date_detection__gte=now() - timedelta(days=7),
            niveau__in=[AlertePrix.NIVEAU_WARNING, AlertePrix.NIVEAU_CRITIQUE],
        )
        .order_by("-date_detection")[:6]
    )

    if not alertes:
        return HttpResponse('<div id="bandeau-alertes-prix" style="display:none;"></div>')

    return render(request, "actualites/_bandeau_prix.html", {"alertes": alertes})


@login_required
def rafraichir_actualites(request: HttpRequest) -> JsonResponse:
    """
    Déclenche manuellement la tâche de collecte.
    Accessible aux staff/superuser uniquement.
    """
    if not request.user.is_staff:
        return JsonResponse({"ok": False, "error": "permission_refusee"}, status=403)

    try:
        from baay.tasks.actualites import fetch_actualites_task
        task = fetch_actualites_task.delay()
        logger.info("Rafraîchissement actualités déclenché manuellement par %s. task_id=%s",
                    request.user.username, task.id)
        return JsonResponse({"ok": True, "task_id": str(task.id)})
    except Exception as exc:
        logger.warning("Rafraîchissement actualités : erreur : %s", exc)
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)
