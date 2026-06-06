# baay/urls_marche.py
from django.urls import path
from .views_marche import (
    graphique_prix_json,
    liste_prix,
    marquer_alerte_vue,
    prix_public_detail,
    prix_public_liste,
)

urlpatterns = [
    path("marche/prix/",                      liste_prix,          name="marche_prix"),
    path("marche/prix/graphique/",            graphique_prix_json, name="marche_prix_graphique"),
    path("marche/prix/alertes/<uuid:pk>/vue/", marquer_alerte_vue, name="marche_alerte_vue"),
    # Pages publiques SEO (data-driven).
    path("prix-marche/",                      prix_public_liste,   name="prix_public"),
    path("prix-marche/<slug:slug>/",          prix_public_detail,  name="prix_public_detail"),
]
