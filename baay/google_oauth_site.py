"""Synchronise django.contrib.sites avec l'hôte OAuth (dev vs prod)."""

from __future__ import annotations

import os

from django.conf import settings


def resolve_site_domain() -> str:
    """
    Domaine utilisé par allauth pour les URLs absolues OAuth.

    - SITE_DOMAIN dans .env : prioritaire (prod / preview Vercel)
    - DEBUG sans SITE_DOMAIN : 127.0.0.1:8000 (aligné Google Console local)
    - Sinon : premier ALLOWED_HOSTS « production » ou fallback Render
    """
    explicit = os.getenv("SITE_DOMAIN", "").strip()
    if explicit:
        return explicit

    if settings.DEBUG:
        return os.getenv("DEV_SITE_DOMAIN", "127.0.0.1:8000").strip() or "127.0.0.1:8000"

    for host in settings.ALLOWED_HOSTS:
        if host not in ("localhost", "127.0.0.1") and not host.startswith("."):
            return host
    return "andd-baay.onrender.com"


def ensure_site_domain() -> str:
    """Met à jour Site (SITE_ID) si le domaine a changé."""
    from django.contrib.sites.models import Site

    domain = resolve_site_domain()
    site, _ = Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={"domain": domain, "name": "Andd Baay"},
    )
    return site.domain
