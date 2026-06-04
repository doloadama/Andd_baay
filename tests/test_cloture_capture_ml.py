"""
Capture ML du rendement réel à la clôture d'un projet.

Vérifie le maillon critique : un rendement réel saisi à la clôture devient un
label d'entraînement (PrevisionFeatures.rendement_reel) marqué RÉEL
(synthetique=False), donc éligible à l'entraînement (≠ données seed). Couvre
aussi le cas où aucune prévision n'existe (le vecteur de features est régénéré
à la volée par la vue avant capture).
"""
import pytest
from django.urls import reverse

from baay.models import PrevisionFeatures, PrevisionRecolte


@pytest.mark.django_db
def test_cloture_capture_label_reel_non_synthetique(client_logged, projet, projet_produit):
    pp = projet_produit
    # À la création du ProjetProduit, un vecteur de features est généré (signal),
    # mais sans label tant que le projet n'est pas clôturé.
    feats = PrevisionFeatures.objects.get(prevision__projet_produit=pp)
    assert feats.rendement_reel is None

    url = reverse("modifier_projet", args=[projet.id])
    resp = client_logged.post(url, {"save_rendement": "1", f"rendement_{pp.id}": "600"})
    assert resp.status_code in (200, 302)

    feats.refresh_from_db()
    assert feats.rendement_reel == 600.0     # label capturé par le signal
    assert feats.synthetique is False        # observation RÉELLE -> entre dans le ML
    pp.refresh_from_db()
    assert float(pp.rendement_final) == 600.0


@pytest.mark.django_db
def test_cloture_sans_features_les_regenere(client_logged, projet, projet_produit):
    """Edge case : si aucune prévision n'existe, la clôture régénère le vecteur
    de features avant de capturer le label (sinon le rendement réel serait perdu)."""
    pp = projet_produit
    # On supprime toute prévision/features existante pour simuler un projet
    # clôturé sans qu'aucune prédiction n'ait été générée pendant la saison.
    PrevisionRecolte.objects.filter(projet_produit=pp).delete()
    assert not PrevisionFeatures.objects.filter(prevision__projet_produit=pp).exists()

    url = reverse("modifier_projet", args=[projet.id])
    resp = client_logged.post(url, {"save_rendement": "1", f"rendement_{pp.id}": "750"})
    assert resp.status_code in (200, 302)

    feats = PrevisionFeatures.objects.get(prevision__projet_produit=pp)
    assert feats.rendement_reel == 750.0
    assert feats.synthetique is False


@pytest.mark.django_db
def test_cloture_sans_rendement_ne_cree_pas_de_label(client_logged, projet, projet_produit):
    """Clôturer sans saisir de rendement ne doit pas fabriquer de faux label."""
    pp = projet_produit
    url = reverse("modifier_projet", args=[projet.id])
    resp = client_logged.post(url, {"save_rendement": "1", f"rendement_{pp.id}": ""})
    assert resp.status_code in (200, 302)

    feats = PrevisionFeatures.objects.filter(prevision__projet_produit=pp).first()
    assert feats is None or feats.rendement_reel is None
