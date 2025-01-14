from django.contrib import admin
from django.urls import path, include
from baay import views

urlpatterns = [
    path('login/', views.login_view, name='login'),  # URL pour la connexion
    path('register/', views.register_view, name='register'),  # URL pour l'inscription
    path('logout/', views.logout_view, name='logout'),  # URL pour la déconnexion
    path('', views.home_view, name='home'),  # Page d'accueil
    path('creer-projet/', views.creer_projet, name='creer_projet'),
    path('projets/', views.liste_projets, name='liste_projets'),
]