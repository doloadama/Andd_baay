import os


def build_message_event_v1(message):
    reply_to = message.reply_to
    sender_user = message.expediteur.user
    return {
        "type": "chat_message_v1",
        "event_version": "v1",
        "event_id": str(message.id),
        "message_id": str(message.id),
        "client_message_id": str(message.client_message_id) if message.client_message_id else None,
        "sender_id": str(message.expediteur_id),
        "sender_username": sender_user.username,
        "sender_name": sender_user.get_full_name() or sender_user.username,
        "contenu": message.contenu,
        "date_envoi": message.date_envoi.strftime("%H:%M"),
        "date_envoi_iso": message.date_envoi.isoformat(),
        "conversation_id": str(message.conversation_id),
        "reply_to_id": str(reply_to.id) if reply_to else None,
        "reply_preview": (
            f"{reply_to.expediteur.user.username}: {reply_to.contenu[:50]}"
            if reply_to
            else None
        ),
        "piece_jointe_url": message.piece_jointe.url if message.piece_jointe else None,
        "piece_jointe_name": os.path.basename(message.piece_jointe.name) if message.piece_jointe else None,
        "is_lu_par_tous": bool(message.is_lu_par_tous()),
    }


def build_read_receipt_event_v1(message_id, reader_profile_id, conversation_id):
    return {
        "type": "chat_read_receipt_v1",
        "event_version": "v1",
        "event_id": f"receipt:{message_id}:{reader_profile_id}",
        "message_id": str(message_id),
        "reader_id": str(reader_profile_id),
        "conversation_id": str(conversation_id),
    }


def build_reaction_updated_event_v1(message_id, conversation_id, reactions):
    return {
        "type": "reaction_updated_v1",
        "event_version": "v1",
        "event_id": f"reaction:{message_id}",
        "message_id": str(message_id),
        "conversation_id": str(conversation_id),
        "reactions": reactions,
    }


def build_inbox_update_event_v1(conversation_id, titre, preview, date_envoi, unread_count, is_online):
    return {
        "type": "inbox_update_v1",
        "event_version": "v1",
        "conversation_id": str(conversation_id),
        "titre": titre,
        "preview": preview,
        "date_envoi": date_envoi.strftime("%d/%m %H:%M") if date_envoi else "",
        "date_envoi_iso": date_envoi.isoformat() if date_envoi else "",
        "unread_count": int(unread_count or 0),
        "is_online": bool(is_online),
    }


def build_unread_count_event_v1(non_lus_total):
    return {
        "type": "unread_count_v1",
        "event_version": "v1",
        "non_lus_total": int(non_lus_total or 0),
    }
