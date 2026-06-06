"""
Prix du marché publics (pilier SEO #3) — data-driven, SEO-safe.

Vérifie : accès public, pages **uniquement** quand des données existent
(jamais de thin-content), balises SEO/JSON-LD, sitemap dynamique, cas vide noindex.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from baay.models import PrixMarche


@pytest.fixture
def prix_mil(db):
    today = date.today()
    PrixMarche.objects.create(
        produit_nom="mil", marche_nom="Kaolack", region="Kaolack",
        prix_unitaire=Decimal("320"), unite="FCFA/kg", source="fao_fpma",
        date_relevee=today - timedelta(days=3),
    )
    PrixMarche.objects.create(
        produit_nom="mil", marche_nom="Dakar-Sandaga", region="Dakar",
        prix_unitaire=Decimal("360"), unite="FCFA/kg", source="oma",
        date_relevee=today - timedelta(days=5),
    )


@pytest.mark.django_db
def test_pilier_public_liste_les_produits_avec_donnees(client, prix_mil):
    r = client.get("/prix-marche/")
    assert r.status_code == 200
    html = r.content.decode()
    assert "Mil" in html
    assert "/prix-marche/mil/" in html
    assert "noindex" not in html        # données présentes → indexable


@pytest.mark.django_db
def test_detail_produit_avec_donnees(client, prix_mil):
    r = client.get("/prix-marche/mil/")
    assert r.status_code == 200
    html = r.content.decode()
    assert "Prix du mil au Sénégal" in html
    assert "Kaolack" in html and "320" in html
    assert 'rel="canonical"' in html
    assert "AggregateOffer" in html and "XOF" in html


@pytest.mark.django_db
def test_slug_inconnu_404(client, prix_mil):
    assert client.get("/prix-marche/produit-bidon/").status_code == 404


@pytest.mark.django_db
def test_produit_connu_sans_donnees_404(client, prix_mil):
    # 'sorgho' est un slug valide mais n'a aucune donnée → pas de thin page.
    assert client.get("/prix-marche/sorgho/").status_code == 404


@pytest.mark.django_db
def test_sitemap_inclut_produit_avec_donnees(client, prix_mil):
    xml = client.get("/sitemap.xml").content.decode()
    assert "/prix-marche/mil/" in xml


@pytest.mark.django_db
def test_cas_vide_noindex_et_sitemap_sans_prix(client):
    """Aucune donnée → pilier noindex, aucune URL prix au sitemap."""
    html = client.get("/prix-marche/").content.decode()
    assert "noindex" in html
    assert "/prix-marche/mil/" not in html
    xml = client.get("/sitemap.xml").content.decode()
    assert "/prix-marche/" not in xml
