from django.urls import path

from .views_messagerie import (
    conversation_detail,
    conversation_messages_older,
    derniere_conversation,
    drawer_conversation_fragment,
    drawer_inbox_fragment,
    messagerie_inbox,
    nouvelle_conversation,
    toggle_reaction,
)

urlpatterns = [
    path("messagerie/", messagerie_inbox, name="messagerie_inbox"),
    path("messagerie/nouvelle/", nouvelle_conversation, name="nouvelle_conversation"),
    path("messagerie/derniere/", derniere_conversation, name="derniere_conversation"),
    path("messagerie/conversation/<uuid:conversation_id>/", conversation_detail, name="conversation_detail"),
    path(
        "messagerie/conversation/<uuid:conversation_id>/messages/anciens/",
        conversation_messages_older,
        name="conversation_messages_older",
    ),
    path("api/messages/<uuid:message_id>/reaction/", toggle_reaction, name="toggle_reaction"),
    path("api/messagerie/drawer/inbox/", drawer_inbox_fragment, name="drawer_inbox_fragment"),
    path("api/messagerie/drawer/conversation/<uuid:conversation_id>/", drawer_conversation_fragment, name="drawer_conversation_fragment"),
]
