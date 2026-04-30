from django.contrib import admin
from django.urls import path, include
from Andd_Baayi import settings
from baay import views
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.conf.urls.static import static
from django.views.generic import TemplateView

from baay.views import CustomPasswordResetView, CustomPasswordResetConfirmView, supprimer_projet

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('confirm-email/<uidb64>/<token>/', views.confirm_email_view, name='confirm_email'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.home_view, name='home'),
    path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline'),
    path('creer-projet/', views.creer_projet, name='creer_projet'),
    path('liste-projets/', views.liste_projets, name='liste_projets'),
    path('projet/<uuid:projet_id>/', views.detail_projet, name='detail_projet'),
    path('projet/<uuid:projet_id>/ajouter-investissement/', views.ajouter_investissement, name='ajouter_investissement'),
    path('projet/<uuid:projet_id>/modifier/', views.modifier_projet, name='modifier_projet'),
    path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path(
        'password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        CustomPasswordResetConfirmView.as_view(),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'),
        name='password_reset_complete',
    ),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profil/', views.profil_view, name='profil'),
    path('get-produit-agricole-details/', views.get_produit_agricole_details, name='get_produit_agricole_details'),
    path('projet/<uuid:projet_id>/generer_prediction/', views.generer_prediction, name='generer_prediction'),
    path('projet/<uuid:projet_id>/supprimer/', supprimer_projet, name='supprimer_projet'),
    path('projets/supprimer/', views.supprimer_projets, name='supprimer_projets'),
    path('api/chatbot/', views.ask_chatbot, name='ask_chatbot'),
    
    # Dashboard API endpoints
    path('api/dashboard/stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('api/dashboard/projets/', views.dashboard_projets_api, name='dashboard_projets_api'),
    path('api/dashboard/filters/', views.dashboard_filters_api, name='dashboard_filters_api'),
    path('api/projet/creer/', views.api_projet_creer, name='api_projet_creer'),
    path('api/projet/bulk-delete/', views.api_projet_bulk_delete, name='api_projet_bulk_delete'),
    path('api/projet/<uuid:projet_id>/statut/', views.update_projet_statut_api, name='update_projet_statut_api'),
    
    # Semis (Sowing) management
    path('semis/', views.liste_semis, name='liste_semis'),
    path('semis/creer/', views.creer_semis, name='creer_semis'),
    path('semis/<uuid:semis_id>/', views.detail_semis, name='detail_semis'),
    path('semis/<uuid:semis_id>/modifier/', views.modifier_semis, name='modifier_semis'),
    path('semis/<uuid:semis_id>/supprimer/', views.supprimer_semis, name='supprimer_semis'),
    path('api/semis/<uuid:semis_id>/statut/', views.update_semis_statut, name='update_semis_statut'),

    # Ferme (Farm) management
    path('fermes/', views.liste_fermes, name='liste_fermes'),
    path('fermes/creer/', views.creer_ferme, name='creer_ferme'),
    path('fermes/<uuid:ferme_id>/', views.detail_ferme, name='detail_ferme'),
    path('fermes/<uuid:ferme_id>/modifier/', views.modifier_ferme, name='modifier_ferme'),
    path('fermes/<uuid:ferme_id>/supprimer/', views.supprimer_ferme, name='supprimer_ferme'),
    path('fermes/<uuid:ferme_id>/membres/ajouter/', views.ajouter_membre_ferme, name='ajouter_membre_ferme'),
    path('fermes/<uuid:ferme_id>/membres/<uuid:membre_id>/retirer/', views.retirer_membre_ferme, name='retirer_membre_ferme'),
    path('fermes/demander-acces/', views.demander_acces_ferme, name='demander_acces_ferme'),
    path('fermes/<uuid:ferme_id>/demandes/<uuid:demande_id>/<str:action>/', views.traiter_demande_acces_ferme, name='traiter_demande_acces_ferme'),

    # Tâches (Tasks)
    path('taches/', views.taches_liste, name='taches_liste'),
    path('taches/creer/', views.creer_tache, name='creer_tache'),
    path('fermes/<uuid:ferme_id>/taches/creer/', views.creer_tache, name='creer_tache_ferme'),
    path('tache/<uuid:tache_id>/', views.tache_detail, name='tache_detail'),

    # Messagerie (Messaging)
    path('messagerie/', views.messagerie_inbox, name='messagerie_inbox'),
    path('messagerie/nouvelle/', views.nouvelle_conversation, name='nouvelle_conversation'),
    path('messagerie/derniere/', views.derniere_conversation, name='derniere_conversation'),
    path('messagerie/conversation/<uuid:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('api/messages/non-lus/', views.api_messages_non_lus, name='api_messages_non_lus'),
    path('api/notifications/', views.api_notifications_list, name='api_notifications_list'),
    path('api/notifications/clear/', views.api_marquer_tout_lu, name='api_marquer_tout_lu'),
    path('api/messages/<uuid:message_id>/reaction/', views.toggle_reaction, name='toggle_reaction'),
    path('api/voice/command/', views.api_voice_command, name='api_voice_command'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
