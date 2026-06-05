"""
Sitemaps SEO — pages publiques indexables d'Andd Baay.

Exposé via /sitemap.xml (cf. Andd_Baayi/urls.py) et référencé dans /robots.txt.
Seules les pages réellement publiques (sans authentification) y figurent ;
les espaces applicatifs (dashboard, projets, admin) restent hors index.
"""
from __future__ import annotations

from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """Pages statiques publiques (accueil + pages légales)."""

    protocol = "https"
    changefreq = "weekly"

    # Noms d'URL publics (cf. baay/urls_core.py, baay/urls_auth.py).
    _PAGES = ["home", "cgu", "confidentialite"]

    def items(self) -> list[str]:
        return self._PAGES

    def location(self, item: str) -> str:
        return reverse(item)

    def priority(self, item: str) -> float:
        return 1.0 if item == "home" else 0.3


sitemaps = {
    "static": StaticViewSitemap,
}
