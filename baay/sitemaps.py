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


class ActualitesSitemap(Sitemap):
    """Hub d'actualités public + pages-hub par catégorie (contenu frais)."""

    protocol = "https"
    changefreq = "daily"
    priority = 0.6

    # Catégories indexables (cf. ArticleActualite.CATEGORIE_CHOICES). "autre" exclu.
    _CATEGORIES = ["meteo", "conseil", "marche", "politique"]

    def items(self) -> list[str]:
        return ["__all__", *self._CATEGORIES]

    def location(self, item: str) -> str:
        if item == "__all__":
            return reverse("actualites")
        return reverse("actualites_categorie", args=[item])


class CalendrierSitemap(Sitemap):
    """Calendrier cultural : page pilier + une fiche par culture (evergreen)."""

    protocol = "https"
    changefreq = "monthly"

    def items(self) -> list[str]:
        from baay.calendrier_cultural import liste_cultures
        return ["__pillar__"] + [c["slug"] for c in liste_cultures()]

    def location(self, item: str) -> str:
        if item == "__pillar__":
            return reverse("calendrier")
        return reverse("calendrier_detail", args=[item])

    def priority(self, item: str) -> float:
        return 0.8 if item == "__pillar__" else 0.7


sitemaps = {
    "static": StaticViewSitemap,
    "actualites": ActualitesSitemap,
    "calendrier": CalendrierSitemap,
}
