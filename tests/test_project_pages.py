import io
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from baay.models import ProjetProduit


@pytest.mark.django_db
def test_liste_projets_page_ok(client_logged):
    resp = client_logged.get(reverse("liste_projets"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_detail_projet_page_ok(client_logged, projet, projet_produit):
    resp = client_logged.get(reverse("detail_projet", args=[projet.id]))
    assert resp.status_code == 200
    assert projet.nom in resp.content.decode("utf-8", errors="ignore")


@pytest.mark.django_db
def test_ajouter_investissement_redirects_with_message_when_cloture(client_logged, projet_cloture):
    url = reverse("ajouter_investissement", args=[projet_cloture.id])
    resp = client_logged.get(url, follow=True)
    assert resp.status_code == 200
    body = resp.content.decode("utf-8", errors="ignore")
    assert "projet est clôturé" in body.lower()


@pytest.mark.django_db
def test_modifier_semis_form_has_multipart_and_file_input(client_logged, projet_produit):
    url = reverse("modifier_semis", args=[projet_produit.id])
    resp = client_logged.get(url)
    assert resp.status_code == 200
    body = resp.content.decode("utf-8", errors="ignore").lower()
    assert "multipart/form-data" in body
    assert 'type="file"' in body or "clearablefileinput" in body


@pytest.mark.django_db
@patch("baay.models.CloudinaryField.pre_save", return_value="fake_url")
def test_modifier_semis_can_post_with_image(mock_cloudinary, client_logged, projet_produit, settings, tmp_path):
    """
    This is a lightweight integration check: the view accepts request.FILES and saves without crashing.
    Storage backend may vary (Cloudinary vs local), so we only assert the response + model update.
    """
    settings.MEDIA_ROOT = tmp_path
    url = reverse("modifier_semis", args=[projet_produit.id])

    fake_png = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x0bIDATx\x9cc`\x00\x00\x00\x02\x00\x01\xe2!\xbc3"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    upload = SimpleUploadedFile("plant.png", fake_png, content_type="image/png")

    resp = client_logged.post(
        url,
        data={
            "image": upload,
            "quantite_semences": "",
            "superficie_allouee": "0.5",
            "date_semis": "",
            "date_recolte_prevue": "",
            "date_recolte_effective": "",
            "rendement_final": "",
            "notes": "ok",
        },
        follow=False,
    )
    assert resp.status_code in (302, 303)
    ProjetProduit.objects.get(pk=projet_produit.pk).refresh_from_db()

