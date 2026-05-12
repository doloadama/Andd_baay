"""
URLs pour la gestion des analyses de sol (front-end).
"""

from django.urls import path
from baay.views_sols import (
    liste_analyses_sol,
    ajouter_analyse_sol,
    detail_analyse_sol,
)

urlpatterns = [
    path("sols/", liste_analyses_sol, name="liste_analyses_sol"),
    path("sols/ajouter/", ajouter_analyse_sol, name="ajouter_analyse_sol"),
    path("sols/<str:analyse_id>/", detail_analyse_sol, name="detail_analyse_sol"),
]
