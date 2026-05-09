import os


def _build_reply_preview(reply_to):
    """Defensively build a 'username: contenu...' preview string for a quoted
    message. Each attribute hop is wrapped in getattr with a None default so
    the broadcast cannot crash on partially-loaded or in-flight cascade-deleted
    related rows. Returns None when there is nothing meaningful to show.
    """
    if reply_to is None:
        return None
    contenu = (getattr(reply_to, "contenu", "") or "")[:50]
    expediteur = getattr(reply_to, "expediteur", None)
    user = getattr(expediteur, "user", None) if expediteur is not None else None
    username = getattr(user, "username", None) if user is not None else None
    if username and contenu:
        return f"{username}: {contenu}"
    if username:
        return f"{username}:"
    return contenu or None


def _message_read_status_from_prefetch(message):
    """
    Compute read-status without triggering extra DB queries.

    Requirements for no extra queries:
    - `message.conversation.participations` prefetched
    - `message.lu_par` prefetched

    Falls back to safe defaults if relations are missing (best-effort payload).
    """
    try:
        # Prefetched objects are stored in `_prefetched_objects_cache`.
        conv_cache = getattr(message.conversation, "_prefetched_objects_cache", None) or {}
        msg_cache = getattr(message, "_prefetched_objects_cache", None) or {}

        participations = list(conv_cache.get("participations") or [])
        lu_par = list(msg_cache.get("lu_par") or [])
    except Exception:
        participations = []
        lu_par = []

    expediteur_id = getattr(message, "expediteur_id", None)
    if expediteur_id is None:
        return False, None, ""

    recipients = [p for p in participations if getattr(p, "profile_id", None) != expediteur_id]
    if not recipients:
        # No recipients (self chat / misconfigured participants): treat as delivered.
        return True, "recu", "Reçu"

    lu_ids = {getattr(p, "id", None) for p in lu_par if getattr(p, "id", None) is not None}

    read_flags = []
    for p in recipients:
        ts = getattr(p, "last_read_at", None)
        par_lu = bool(ts is not None and ts >= message.date_envoi)
        if not par_lu and getattr(p, "profile_id", None) in lu_ids:
            par_lu = True
        read_flags.append(par_lu)

    if all(read_flags):
        return True, "recu", "Reçu"
    if any(read_flags):
        return False, "recu_partiel", "Reçu (partiel)"
    return False, "envoye", "Envoyé"


def build_message_event_v1(message):
    reply_to = message.reply_to
    sender_user = message.expediteur.user
    is_lu_par_tous, lecture_statut, lecture_statut_label = _message_read_status_from_prefetch(message)
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
        "reply_preview": _build_reply_preview(reply_to),
        "piece_jointe_url": message.piece_jointe.url if message.piece_jointe else None,
        "piece_jointe_name": os.path.basename(message.piece_jointe.name) if message.piece_jointe else None,
        "is_lu_par_tous": bool(is_lu_par_tous),
        "lecture_statut": lecture_statut,
        "lecture_statut_label": lecture_statut_label,
    }


def build_read_receipt_event_v1(message_id, reader_profile_id, conversation_id, lecture_statut=None):
    payload = {
        "type": "chat_read_receipt_v1",
        "event_version": "v1",
        "event_id": f"receipt:{message_id}:{reader_profile_id}",
        "message_id": str(message_id),
        "reader_id": str(reader_profile_id),
        "conversation_id": str(conversation_id),
    }
    if lecture_statut:
        payload["lecture_statut"] = lecture_statut
    return payload


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


def build_inbox_update_event_v1_light(conversation_id, titre, preview, date_envoi, *, unread_delta=0, is_online=False):
    """
    Lightweight inbox update for eventual consistency.

    - Does NOT include an exact unread_count (avoids DB counting on send).
    - Includes an `unread_delta` hint for client-side badge estimates.
    """
    return {
        "type": "inbox_update_v1",
        "event_version": "v1",
        "conversation_id": str(conversation_id),
        "titre": titre,
        "preview": preview,
        "date_envoi": date_envoi.strftime("%d/%m %H:%M") if date_envoi else "",
        "date_envoi_iso": date_envoi.isoformat() if date_envoi else "",
        "unread_count": None,
        "unread_delta": int(unread_delta or 0),
        "is_online": bool(is_online),
    }


def build_unread_count_event_v1(non_lus_total):
    return {
        "type": "unread_count_v1",
        "event_version": "v1",
        "non_lus_total": int(non_lus_total or 0),
    }


def build_recruitment_status_event_v1(demande, statut):
    ferme = getattr(demande, "ferme", None)
    utilisateur = getattr(demande, "utilisateur", None)
    user = getattr(utilisateur, "user", None) if utilisateur is not None else None
    milestone = (
        "recruitment_approved" if statut == "approuvee" else
        "recruitment_refused" if statut == "refusee" else
        "recruitment_updated"
    )
    return {
        "type": "milestone_update_v1",
        "event_version": "v1",
        "event_id": f"recruitment:{getattr(demande, 'id', '0')}",
        "milestone": milestone,
        "statut": statut,
        "demande_id": str(getattr(demande, "id", "")),
        "ferme_id": str(getattr(ferme, "id", "")) if ferme is not None else None,
        "ferme_nom": getattr(ferme, "nom", None) if ferme is not None else None,
        "user_id": str(getattr(utilisateur, "id", "")) if utilisateur is not None else None,
        "username": getattr(user, "username", None) if user is not None else None,
    }
