from django.contrib import admin
from django.urls import path, include
from baay import views

urlpatterns = [
    path('login/', views.login_view, name='login'),  # URL pour la connexion
    path('register/', views.register_view, name='register'),  # URL pour l'inscription
    path('logout/', views.logout_view, name='logout'),  # URL pour la déconnexion
    path('', views.home_view, name='home'),  # Page d'accueil
    path('creer-projet/', views.creer_projet, name='creer_projet'),
    path('liste-projets/', views.liste_projets, name='liste_projets'),
    path('projet/<uuid:projet_id>/', views.detail_projet, name='detail_projet'),
    path('projet/<uuid:projet_id>/ajouter-investissement/', views.ajouter_investissement, name='ajouter_investissement'),
    path('projet/<uuid:projet_id>/modifier/', views.modifier_projet, name='modifier_projet'),
    path('projet/<uuid:projet_id>/supprimer/', views.supprimer_projet, name='supprimer_projet'),
]
