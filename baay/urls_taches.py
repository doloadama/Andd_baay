from django.urls import path

from .views_taches import creer_tache, tache_detail, taches_liste

urlpatterns = [
    path("taches/", taches_liste, name="taches_liste"),
    path("taches/creer/", creer_tache, name="creer_tache"),
    path("fermes/<uuid:ferme_id>/taches/creer/", creer_tache, name="creer_tache_ferme"),
    path("tache/<uuid:tache_id>/", tache_detail, name="tache_detail"),
]
