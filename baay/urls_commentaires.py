from django.urls import path

from baay.views_commentaires import ajouter_commentaire

urlpatterns = [
    path("commentaires/<int:ct_id>/<uuid:object_id>/", ajouter_commentaire, name="ajouter_commentaire"),
]
