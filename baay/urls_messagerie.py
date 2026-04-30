from django.urls import path

from .views_messagerie import (
    conversation_detail,
    derniere_conversation,
    messagerie_inbox,
    nouvelle_conversation,
    toggle_reaction,
)

urlpatterns = [
    path("messagerie/", messagerie_inbox, name="messagerie_inbox"),
    path("messagerie/nouvelle/", nouvelle_conversation, name="nouvelle_conversation"),
    path("messagerie/derniere/", derniere_conversation, name="derniere_conversation"),
    path("messagerie/conversation/<uuid:conversation_id>/", conversation_detail, name="conversation_detail"),
    path("api/messages/<uuid:message_id>/reaction/", toggle_reaction, name="toggle_reaction"),
]
