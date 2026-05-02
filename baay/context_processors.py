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
        "investissement" in u
        or "finance" in u
    )

    return {
        "show_finance_nav": show,
        "finance_section_active": active,
    }
