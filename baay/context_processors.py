def exploitation_section(request):
    """Indique si la vue courante est Fermes / Projets / Semis (menu Exploitation)."""
    rm = getattr(request, "resolver_match", None)
    u = (rm.url_name or "") if rm else ""
    active = bool(u) and (
        "ferme" in u or "projet" in u or "semis" in u
    )
    return {"exploitation_section_active": active}
