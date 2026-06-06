"""
Actualités publiques indexables (pilier SEO #1).

Vérifie : accès public (sans login), pages-hub par catégorie, anti-duplicate
(on republie le `resume`, jamais le `contenu`), balises SEO et présence au sitemap.
"""
import pytest

from baay.models import ArticleActualite


@pytest.fixture
def articles(db):
    a = ArticleActualite.objects.create(
        source="anacim", categorie="meteo",
        titre="Pluies attendues sur Kaolack cette semaine",
        resume="Resume court et visible dans la carte.",
        contenu="CONTENU_INTEGRAL_SENTINEL_NE_PAS_REPUBLIER",
        url_originale="https://example.org/anacim/pluies-kaolack",
    )
    b = ArticleActualite.objects.create(
        source="autre", categorie="marche",
        titre="Hausse du prix du mil sur les marches",
        resume="Le prix du mil augmente.",
        contenu="autre contenu integral",
        url_originale="https://example.org/marche/prix-mil",
    )
    return a, b


@pytest.mark.django_db
def test_liste_actualites_publique_sans_login(client, articles):
    """La page est accessible aux visiteurs anonymes (indexable)."""
    r = client.get("/actualites/")
    assert r.status_code == 200
    html = r.content.decode()
    assert "Pluies attendues sur Kaolack" in html


@pytest.mark.django_db
def test_page_hub_categorie_filtre(client, articles):
    r = client.get("/actualites/meteo/")
    assert r.status_code == 200
    html = r.content.decode()
    assert "Pluies attendues sur Kaolack" in html      # meteo
    assert "Hausse du prix du mil" not in html          # marche, filtré


@pytest.mark.django_db
def test_categorie_inconnue_404(client, articles):
    assert client.get("/actualites/categorie-bidon/").status_code == 404


@pytest.mark.django_db
def test_anti_duplicate_content(client, articles):
    """On affiche le resume, jamais le contenu intégral (anti-duplicate SEO)."""
    html = client.get("/actualites/").content.decode()
    assert "Resume court et visible" in html
    assert "CONTENU_INTEGRAL_SENTINEL_NE_PAS_REPUBLIER" not in html


@pytest.mark.django_db
def test_balises_seo_presentes(client, articles):
    html = client.get("/actualites/meteo/").content.decode()
    assert 'rel="canonical"' in html
    assert "application/ld+json" in html
    assert "CollectionPage" in html
    assert "Météo &amp; agroclimat au Sénégal" in html or "agroclimat" in html


@pytest.mark.django_db
def test_sitemap_inclut_actualites(client, articles):
    xml = client.get("/sitemap.xml").content.decode()
    assert "/actualites/" in xml
    assert "/actualites/meteo/" in xml
