"""
Calendrier cultural public (pilier SEO #2) : accès public, SEO, sitemap,
cohérence du dataset curé.
"""
import pytest

from baay.calendrier_cultural import get_culture, liste_cultures


@pytest.mark.django_db
def test_pilier_public(client):
    r = client.get("/calendrier-cultural/")
    assert r.status_code == 200
    html = r.content.decode()
    assert "Calendrier cultural du Sénégal" in html
    assert "Arachide" in html and "Mil" in html


@pytest.mark.django_db
def test_detail_public_et_seo(client):
    r = client.get("/calendrier-cultural/arachide/")
    assert r.status_code == 200
    html = r.content.decode()
    assert "Calendrier cultural" in html and "arachide" in html.lower()
    assert 'rel="canonical"' in html
    assert "application/ld+json" in html
    assert "FAQPage" in html
    # Article français correct dans le dataset (évite « du Arachide »).
    assert get_culture("arachide")["det_de"] == "de l'arachide"


@pytest.mark.django_db
def test_detail_slug_inconnu_404(client):
    assert client.get("/calendrier-cultural/culture-bidon/").status_code == 404


@pytest.mark.django_db
def test_sitemap_inclut_calendrier(client):
    xml = client.get("/sitemap.xml").content.decode()
    assert "/calendrier-cultural/" in xml
    assert "/calendrier-cultural/arachide/" in xml


def test_dataset_coherence():
    """Chaque culture a un slug résolvable et tous les champs requis non vides."""
    requis = (
        "nom", "famille", "saison", "semis_mois", "cycle_jours", "besoin_eau_mm",
        "periode_recolte", "rendement_min", "rendement_max", "sols_adaptes",
        "conseils", "det", "det_de", "meta_description", "intro",
    )
    for c in liste_cultures():
        assert get_culture(c["slug"]) is c
        for champ in requis:
            assert c.get(champ), f"{c['slug']} : champ '{champ}' manquant/vide"
        assert 1 <= min(c["semis_mois"]) and max(c["semis_mois"]) <= 12
