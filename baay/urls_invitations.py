from django.urls import path
from baay.views_invitation import creer_invitation, rejoindre_ferme

urlpatterns = [
    path('invitations/ferme/<uuid:ferme_id>/creer/', creer_invitation, name='creer_invitation'),
    path('rejoindre/<str:token>/', rejoindre_ferme, name='rejoindre_ferme'),
]
