def exploitation_section(request):
    """Indique si la vue courante est Fermes / Projets / Semis (menu Exploitation)."""
    rm = getattr(request, "resolver_match", None)
    u = (rm.url_name or "") if rm else ""
    active = bool(u) and (
        "ferme" in u or "projet" in u or "semis" in u
    )
    return {"exploitation_section_active": active}


def finance_section(request):
    """Menu Finance : réservé aux membres Propriétaire / Manager (MembreFerme)."""
    from baay.permissions import peut_acceder_menu_finance

    show = False
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        show = peut_acceder_menu_finance(profile)

    rm = getattr(request, "resolver_match", None)
    u = (rm.url_name or "") if rm else ""
    active = show and bool(u) and (
        u == "finance_hub"
        or u == "ajouter_investissement"
        or ("finance_" in u)
        or ("investissement" in u)
    )

    return {
        "show_finance_nav": show,
        "finance_section_active": active,
    }


def cooperative_nav(request):
    """Affiche le lien Dashboard Coopérative si l'owner gère au moins 2 fermes."""
    show = False
    if request.user.is_authenticated:
        from baay.models import Ferme
        profile = getattr(request.user, "profile", None)
        if profile:
            show = Ferme.objects.filter(proprietaire=profile).count() >= 2
    return {"show_cooperative_nav": show}


def auth_backgrounds(request):
    """
    Injecte les URLs de fond d'écran pour les pages d'authentification.
    Utilise Cloudinary si disponible, sinon fallback sur les fichiers statiques.
    """
    from baay.services import get_auth_background_urls
    return get_auth_background_urls()


def cloudinary_config(request):
    """
    Injecte la configuration Cloudinary pour le widget d'upload direct.
    """
    from django.conf import settings
    return {
        'CLOUDINARY_CLOUD_NAME': getattr(settings, 'CLOUDINARY_CLOUD_NAME', ''),
        'CLOUDINARY_UPLOAD_PRESET': getattr(settings, 'CLOUDINARY_UPLOAD_PRESET', ''),
    }
