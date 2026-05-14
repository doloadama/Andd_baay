from django.urls import path

from .views_fermes import (
    ajouter_membre_ferme,
    creer_ferme,
    demander_acces_ferme,
    detail_ferme,
    historique_sol_ferme,
    liste_fermes,
    modifier_ferme,
    regenerer_code_acces_ferme,
    retirer_membre_ferme,
    supprimer_ferme,
    traiter_demande_acces_ferme,
)
from .views_inventory import (
    ajouter_intrant,
    ajouter_recolte,
    ajuster_intrant_htmx,
    liste_inventaire,
    modifier_intrant,
    supprimer_intrant,
)

urlpatterns = [
    path("fermes/", liste_fermes, name="liste_fermes"),
    path("fermes/creer/", creer_ferme, name="creer_ferme"),
    path("fermes/<uuid:ferme_id>/code-acces/regenerer/", regenerer_code_acces_ferme, name="regenerer_code_acces_ferme"),
    path("fermes/<uuid:ferme_id>/", detail_ferme, name="detail_ferme"),
    path("fermes/<uuid:ferme_id>/sols/", historique_sol_ferme, name="historique_sol_ferme"),
    path("fermes/<uuid:ferme_id>/modifier/", modifier_ferme, name="modifier_ferme"),
    path("fermes/<uuid:ferme_id>/supprimer/", supprimer_ferme, name="supprimer_ferme"),
    path("fermes/<uuid:ferme_id>/membres/ajouter/", ajouter_membre_ferme, name="ajouter_membre_ferme"),
    path("fermes/<uuid:ferme_id>/membres/<uuid:membre_id>/retirer/", retirer_membre_ferme, name="retirer_membre_ferme"),
    path("fermes/demander-acces/", demander_acces_ferme, name="demander_acces_ferme"),
    path("fermes/<uuid:ferme_id>/demandes/<uuid:demande_id>/<str:action>/", traiter_demande_acces_ferme, name="traiter_demande_acces_ferme"),
    # Inventaire
    path("fermes/<uuid:ferme_id>/inventaire/", liste_inventaire, name="liste_inventaire"),
    path("fermes/<uuid:ferme_id>/inventaire/intrants/ajouter/", ajouter_intrant, name="ajouter_intrant"),
    path("fermes/<uuid:ferme_id>/inventaire/intrants/<uuid:intrant_id>/modifier/", modifier_intrant, name="modifier_intrant"),
    path("fermes/<uuid:ferme_id>/inventaire/intrants/<uuid:intrant_id>/ajuster/", ajuster_intrant_htmx, name="ajuster_intrant_htmx"),
    path("fermes/<uuid:ferme_id>/inventaire/intrants/<uuid:intrant_id>/supprimer/", supprimer_intrant, name="supprimer_intrant"),
    path("fermes/<uuid:ferme_id>/inventaire/recoltes/ajouter/", ajouter_recolte, name="ajouter_recolte"),
]
