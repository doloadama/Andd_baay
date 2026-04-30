from django.urls import path

from .views_semis import (
    creer_semis,
    detail_semis,
    liste_semis,
    modifier_semis,
    supprimer_semis,
    update_semis_statut,
)

urlpatterns = [
    path("semis/", liste_semis, name="liste_semis"),
    path("semis/creer/", creer_semis, name="creer_semis"),
    path("semis/<uuid:semis_id>/", detail_semis, name="detail_semis"),
    path("semis/<uuid:semis_id>/modifier/", modifier_semis, name="modifier_semis"),
    path("semis/<uuid:semis_id>/supprimer/", supprimer_semis, name="supprimer_semis"),
    path("api/semis/<uuid:semis_id>/statut/", update_semis_statut, name="update_semis_statut"),
]
