"""
SEO Quick Wins — robots.txt, sitemap.xml et balises <head> indexables.
"""
import pytest


@pytest.mark.django_db
def test_robots_txt(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "text/plain" in r["Content-Type"]
    body = r.content.decode()
    assert body.startswith("User-agent: *")
    assert "Sitemap:" in body and "/sitemap.xml" in body


@pytest.mark.django_db
def test_sitemap_xml(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert "xml" in r["Content-Type"]
    assert b"<loc>" in r.content


@pytest.mark.django_db
def test_home_head_seo_tags(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.content.decode()
    for needle in (
        'rel="canonical"',
        "application/ld+json",
        'property="og:image"',
        'name="twitter:card"',
        'property="og:site_name"',
    ):
        assert needle in html, f"balise SEO manquante : {needle}"
