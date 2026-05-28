# baay/urls_marche.py
from django.urls import path
from .views_marche import graphique_prix_json, liste_prix, marquer_alerte_vue

urlpatterns = [
    path("marche/prix/",                      liste_prix,          name="marche_prix"),
    path("marche/prix/graphique/",            graphique_prix_json, name="marche_prix_graphique"),
    path("marche/prix/alertes/<uuid:pk>/vue/", marquer_alerte_vue, name="marche_alerte_vue"),
]
