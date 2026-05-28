# baay/urls_actualites.py
from django.urls import path

from .views_actualites import liste_actualites, rafraichir_actualites

urlpatterns = [
    path("actualites/", liste_actualites, name="actualites"),
    path("actualites/rafraichir/", rafraichir_actualites, name="actualites_rafraichir"),
]
