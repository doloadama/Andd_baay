from django.urls import path

from .views_cooperative import (
    cooperative_detail,
    rejoindre_cooperative,
    rattacher_ferme_cooperative,
    detacher_ferme_cooperative,
    cooperative_changer_role,
    cooperative_retirer_membre,
)

urlpatterns = [
    path("cooperatives/rejoindre/", rejoindre_cooperative, name="rejoindre_cooperative"),
    path("cooperatives/<uuid:coop_id>/", cooperative_detail, name="cooperative_detail"),
    path("cooperatives/<uuid:coop_id>/rattacher-ferme/", rattacher_ferme_cooperative, name="rattacher_ferme_cooperative"),
    path("cooperatives/<uuid:coop_id>/detacher-ferme/", detacher_ferme_cooperative, name="detacher_ferme_cooperative"),
    path("cooperatives/<uuid:coop_id>/membre/<uuid:membre_id>/role/", cooperative_changer_role, name="cooperative_changer_role"),
    path("cooperatives/<uuid:coop_id>/membre/<uuid:membre_id>/retirer/", cooperative_retirer_membre, name="cooperative_retirer_membre"),
]
