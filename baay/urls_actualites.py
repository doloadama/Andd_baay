# baay/urls_actualites.py
from django.urls import path

from .views_actualites import bandeau_alertes_prix, liste_actualites, rafraichir_actualites

urlpatterns = [
    path("actualites/", liste_actualites, name="actualites"),
    path("actualites/rafraichir/", rafraichir_actualites, name="actualites_rafraichir"),
    path("actualites/bandeau-prix/", bandeau_alertes_prix, name="actualites_bandeau_prix"),
    # Page-hub indexable par catégorie (APRÈS les routes spécifiques ci-dessus).
    path("actualites/<slug:categorie>/", liste_actualites, name="actualites_categorie"),
]
