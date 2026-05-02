from django.urls import path

from .views_fermes import (
    ajouter_membre_ferme,
    creer_ferme,
    demander_acces_ferme,
    detail_ferme,
    liste_fermes,
    modifier_ferme,
    regenerer_code_acces_ferme,
    retirer_membre_ferme,
    supprimer_ferme,
    traiter_demande_acces_ferme,
)

urlpatterns = [
    path("fermes/", liste_fermes, name="liste_fermes"),
    path("fermes/creer/", creer_ferme, name="creer_ferme"),
    path("fermes/<uuid:ferme_id>/code-acces/regenerer/", regenerer_code_acces_ferme, name="regenerer_code_acces_ferme"),
    path("fermes/<uuid:ferme_id>/", detail_ferme, name="detail_ferme"),
    path("fermes/<uuid:ferme_id>/modifier/", modifier_ferme, name="modifier_ferme"),
    path("fermes/<uuid:ferme_id>/supprimer/", supprimer_ferme, name="supprimer_ferme"),
    path("fermes/<uuid:ferme_id>/membres/ajouter/", ajouter_membre_ferme, name="ajouter_membre_ferme"),
    path("fermes/<uuid:ferme_id>/membres/<uuid:membre_id>/retirer/", retirer_membre_ferme, name="retirer_membre_ferme"),
    path("fermes/demander-acces/", demander_acces_ferme, name="demander_acces_ferme"),
    path("fermes/<uuid:ferme_id>/demandes/<uuid:demande_id>/<str:action>/", traiter_demande_acces_ferme, name="traiter_demande_acces_ferme"),
]
