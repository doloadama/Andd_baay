from django.urls import path

from .views_projets import (
    ajouter_investissement,
    creer_projet,
    detail_projet,
    generer_prediction,
    get_produit_agricole_details,
    liste_projets,
    modifier_projet,
    supprimer_projet,
    supprimer_projets,
    update_projet_statut_api,
)

urlpatterns = [
    path("creer-projet/", creer_projet, name="creer_projet"),
    path("liste-projets/", liste_projets, name="liste_projets"),
    path("projet/<uuid:projet_id>/", detail_projet, name="detail_projet"),
    path("projet/<uuid:projet_id>/ajouter-investissement/", ajouter_investissement, name="ajouter_investissement"),
    path("projet/<uuid:projet_id>/modifier/", modifier_projet, name="modifier_projet"),
    path("projet/<uuid:projet_id>/generer_prediction/", generer_prediction, name="generer_prediction"),
    path("projet/<uuid:projet_id>/supprimer/", supprimer_projet, name="supprimer_projet"),
    path("projets/supprimer/", supprimer_projets, name="supprimer_projets"),
    path("get-produit-agricole-details/", get_produit_agricole_details, name="get_produit_agricole_details"),
    path("api/projet/<uuid:projet_id>/statut/", update_projet_statut_api, name="update_projet_statut_api"),
]
