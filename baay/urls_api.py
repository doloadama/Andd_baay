from django.urls import path

from .views_api import (
    api_conversation_sync,
    api_marquer_tout_lu,
    api_messages_non_lus,
    api_notifications_list,
    api_projet_bulk_delete,
    api_projet_creer,
    api_voice_command,
    ask_chatbot,
    dashboard_filters_api,
    dashboard_projets_api,
    dashboard_stats_api,
)

urlpatterns = [
    path("api/chatbot/", ask_chatbot, name="ask_chatbot"),
    path("api/dashboard/stats/", dashboard_stats_api, name="dashboard_stats_api"),
    path("api/dashboard/projets/", dashboard_projets_api, name="dashboard_projets_api"),
    path("api/dashboard/filters/", dashboard_filters_api, name="dashboard_filters_api"),
    path("api/projet/creer/", api_projet_creer, name="api_projet_creer"),
    path("api/projet/bulk-delete/", api_projet_bulk_delete, name="api_projet_bulk_delete"),
    path("api/messages/non-lus/", api_messages_non_lus, name="api_messages_non_lus"),
    path("api/messagerie/conversation/<uuid:conversation_id>/sync/", api_conversation_sync, name="api_conversation_sync"),
    path("api/notifications/", api_notifications_list, name="api_notifications_list"),
    path("api/notifications/clear/", api_marquer_tout_lu, name="api_marquer_tout_lu"),
    path("api/voice/command/", api_voice_command, name="api_voice_command"),
]
