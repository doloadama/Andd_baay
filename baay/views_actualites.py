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
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import ArticleActualite

logger = logging.getLogger(__name__)

_PAGE_SIZE = 24


@login_required
@require_GET
def liste_actualites(request: HttpRequest) -> HttpResponse:
    """
    Page principale des actualités agro-météo.
    Filtres : source, categorie (GET params).
    """
    source    = request.GET.get("source", "").strip()
    categorie = request.GET.get("categorie", "").strip()

    qs = ArticleActualite.objects.filter(actif=True)

    if source and source in dict(ArticleActualite.SOURCE_CHOICES):
        qs = qs.filter(source=source)
    if categorie and categorie in dict(ArticleActualite.CATEGORIE_CHOICES):
        qs = qs.filter(categorie=categorie)

    paginator = Paginator(qs, _PAGE_SIZE)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    context = {
        "page_obj":        page_obj,
        "source_actif":    source,
        "categorie_actif": categorie,
        "sources":         ArticleActualite.SOURCE_CHOICES,
        "categories":      ArticleActualite.CATEGORIE_CHOICES,
        "total":           qs.count(),
    }
    return render(request, "actualites/liste.html", context)


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
