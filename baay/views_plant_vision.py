"""
Vues HTMX pour l'analyse IA des photos de culture (BaayVision).
"""

import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from baay.models import AnalyseImageCulture, ProjetProduit
from baay.permissions import peut_modifier_semis, peut_voir_semis
from baay.tasks.plant_vision import run_analyse_image_culture

logger = logging.getLogger(__name__)

RATE_LIMIT_KEY = "plant_vision_rl:{user_id}"
RATE_LIMIT_MAX = 15
RATE_LIMIT_WINDOW = 60


def _plant_vision_configured() -> bool:
    return bool(getattr(settings, "GEMINI_API_KEYS", None) or getattr(settings, "GEMINI_API_KEY", ""))


def _check_rate_limit(user_id: int) -> bool:
    key = RATE_LIMIT_KEY.format(user_id=user_id)
    count = cache.get(key, 0)
    if count >= RATE_LIMIT_MAX:
        return False
    cache.set(key, count + 1, timeout=RATE_LIMIT_WINDOW)
    return True


def _get_analyse_panel_context(request: HttpRequest, pp: ProjetProduit) -> dict:
    derniere = (
        AnalyseImageCulture.objects.filter(projet_produit=pp)
        .order_by("-date_creation")
        .first()
    )
    return {
        "projet_produit": pp,
        "semis": pp,
        "derniere_analyse": derniere,
        "peut_lancer_analyse": (
            bool(pp.image)
            and peut_modifier_semis(request.user.profile, pp)
            and _plant_vision_configured()
        ),
        "vision_disponible": _plant_vision_configured(),
    }


@login_required
@require_GET
def partial_analyse_semis(request: HttpRequest, semis_id) -> HttpResponse:
    """Panneau HTMX : état de l'analyse ou formulaire de lancement."""
    pp = get_object_or_404(
        ProjetProduit.objects.select_related("produit", "projet__ferme"),
        pk=semis_id,
    )
    if not peut_voir_semis(request.user.profile, pp):
        return HttpResponse("Accès refusé.", status=403)

    analyse_id = request.GET.get("analyse_id")
    if analyse_id:
        analyse = get_object_or_404(
            AnalyseImageCulture,
            pk=analyse_id,
            projet_produit=pp,
        )
        if analyse.statut in (
            AnalyseImageCulture.STATUT_EN_ATTENTE,
            AnalyseImageCulture.STATUT_EN_COURS,
        ):
            return render(
                request,
                "semis/_analyse_ia_loading.html",
                {"analyse": analyse, "projet_produit": pp},
            )
        return render(
            request,
            "semis/_analyse_ia_result.html",
            {
                "analyse": analyse,
                "projet_produit": pp,
                **_get_analyse_panel_context(request, pp),
            },
        )

    return render(
        request,
        "semis/_analyse_ia_panel.html",
        _get_analyse_panel_context(request, pp),
    )


@login_required
@require_POST
def lancer_analyse_semis(request: HttpRequest, semis_id) -> HttpResponse:
    """Démarre une analyse IA sur la photo de la culture."""
    pp = get_object_or_404(
        ProjetProduit.objects.select_related("produit", "projet__ferme"),
        pk=semis_id,
    )
    if not peut_modifier_semis(request.user.profile, pp):
        return HttpResponse("Accès refusé.", status=403)

    if not pp.image:
        return render(
            request,
            "semis/_analyse_ia_panel.html",
            {
                **_get_analyse_panel_context(request, pp),
                "erreur_analyse": "Ajoutez une photo avant de lancer l'analyse.",
            },
        )

    if not _plant_vision_configured():
        return render(
            request,
            "semis/_analyse_ia_panel.html",
            {
                **_get_analyse_panel_context(request, pp),
                "erreur_analyse": "L'analyse IA n'est pas configurée sur ce serveur.",
            },
        )

    if not _check_rate_limit(request.user.id):
        return render(
            request,
            "semis/_analyse_ia_panel.html",
            {
                **_get_analyse_panel_context(request, pp),
                "erreur_analyse": "Trop de requêtes. Réessayez dans une minute.",
            },
        )

    analyse = AnalyseImageCulture.objects.create(
        projet_produit=pp,
        demandee_par=request.user.profile,
        type_analyse=AnalyseImageCulture.TYPE_PLANT_PEST,
        statut=AnalyseImageCulture.STATUT_EN_ATTENTE,
    )
    run_analyse_image_culture.delay(str(analyse.id))

    return render(
        request,
        "semis/_analyse_ia_loading.html",
        {
            "analyse": analyse,
            "projet_produit": pp,
        },
    )
