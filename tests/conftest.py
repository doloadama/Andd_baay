import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from baay.models import Ferme, Localite, Pays, ProduitAgricole, Projet, ProjetProduit


@pytest.fixture
def user(db):
    return User.objects.create_user(username="u1", password="pass12345")


@pytest.fixture
def client_logged(client, user):
    assert client.login(username="u1", password="pass12345")
    return client


@pytest.fixture
def geo(db):
    pays = Pays.objects.create(nom="Senegal")
    loc = Localite.objects.create(nom="Dakar", pays=pays, latitude=14.7, longitude=-17.4)
    return pays, loc


@pytest.fixture
def ferme(user, geo):
    _pays, loc = geo
    return Ferme.objects.create(
        nom="Ferme Test",
        proprietaire=user.profile,
        localite=loc,
        pays=_pays,
        latitude=14.7,
        longitude=-17.4,
        superficie_totale=10,
    )


@pytest.fixture
def produit(db):
    return ProduitAgricole.objects.create(nom="Tomate", rendement_moyen=1200)


@pytest.fixture
def projet(user, ferme, geo):
    _pays, loc = geo
    return Projet.objects.create(
        nom="Projet A",
        utilisateur=user.profile,
        ferme=ferme,
        localite=loc,
        pays=_pays,
        superficie=1,
        date_lancement=timezone.localdate(),
        statut="en_cours",
    )


@pytest.fixture
def projet_cloture(projet):
    # Model validation requires "cloture" only after "fini"
    projet.statut = "fini"
    projet.save(update_fields=["statut"])
    projet.statut = "cloture"
    projet.save(update_fields=["statut"])
    return projet


@pytest.fixture
def projet_produit(projet, produit):
    return ProjetProduit.objects.create(
        projet=projet,
        produit=produit,
        superficie_allouee=0.5,
    )

