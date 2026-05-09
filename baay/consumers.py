import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Prefetch

from .messaging_contract import build_read_receipt_event_v1


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        conv_id = self.scope['url_route']['kwargs'].get('conversation_id')
        if not conv_id or not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # Verify user is a participant
        self.conv_id = str(conv_id)
        is_participant = await self._check_participation(self.conv_id, self.user.id)
        if not is_participant:
            await self.close()
            return

        self.group_name = f"conversation_{self.conv_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"type": "error_v1", "error": "invalid_json"}))
            return
        msg_type = data.get('type')
        if not await self._check_participation(self.conv_id, self.user.id):
            await self.close()
            return
        if msg_type in {'typing', 'chat_typing_v1'}:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_typing_v1',
                    'event_version': 'v1',
                    'sender_id': str(self.user.id),
                    'sender_username': self.user.username,
                }
            )
        elif msg_type in {'stop_typing', 'chat_stop_typing_v1'}:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_stop_typing_v1',
                    'event_version': 'v1',
                    'sender_id': str(self.user.id),
                }
            )
        elif msg_type in {'read_receipt', 'read_receipt_v1'}:
            message_id = data.get('message_id')
            # Returns (message_id, profile_id) atomically, or None on any failure.
            # Doing both lookups in one DB transaction eliminates the race where
            # the profile could be deleted between mark + broadcast, leaving the
            # message marked as read but no receipt event emitted.
            result = await self._mark_message_read(self.conv_id, self.user.id, message_id)
            if result is not None:
                valid_message_id, reader_profile_id, lecture_statut = result
                await self.channel_layer.group_send(
                    self.group_name,
                    build_read_receipt_event_v1(
                        valid_message_id,
                        reader_profile_id,
                        self.conv_id,
                        lecture_statut=lecture_statut,
                    ),
                )

    async def chat_message_v1(self, event):
        """Broadcast a new message to the group."""
        await self.send(text_data=json.dumps(event))

    async def chat_message(self, event):
        """Backward-compatible event relay."""
        await self.send(text_data=json.dumps(event))

    async def chat_typing_v1(self, event):
        """Someone is typing."""
        await self.send(text_data=json.dumps(event))

    async def chat_stop_typing_v1(self, event):
        """Someone stopped typing."""
        await self.send(text_data=json.dumps(event))

    async def chat_read_receipt_v1(self, event):
        """Someone read a message."""
        await self.send(text_data=json.dumps(event))

    async def reaction_updated_v1(self, event):
        """Reaction state changed for a message."""
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def _check_participation(self, conv_id, user_id):
        from .models import Conversation, Profile
        try:
            profile = Profile.objects.get(user_id=user_id)
            return Conversation.objects.filter(id=conv_id, participants=profile).exists()
        except Profile.DoesNotExist:
            return False

    @database_sync_to_async
    def _mark_message_read(self, conv_id, user_id, message_id):
        """Mark a message as read by the given user inside a single sync block.

        Returns a (message_id, profile_id) tuple on success, or None on any
        validation failure (no profile, missing message, not a participant).
        Returning both ids together prevents an inconsistency where the side
        effect (lu_par.add) lands but the broadcast is skipped because a
        follow-up profile lookup race-loses against a profile deletion.
        """
        from .models import Message, Profile, ParticipationConversation, bump_participation_last_read
        from django.db.models import Count, Q
        try:
            profile = Profile.objects.get(user_id=user_id)
            msg = Message.objects.filter(conversation_id=conv_id, id=message_id).first()
            if msg is None:
                return None
            if not msg.conversation.participants.filter(id=profile.id).exists():
                return None
            msg.lu_par.add(profile)
            bump_participation_last_read(conv_id, profile.id, msg.date_envoi)
            # Compute sender-side delivery status without re-fetching the message graph.
            # We use ParticipationConversation.last_read_at as the source of truth:
            # - envoye: nobody has read past message timestamp
            # - recu_partiel: some have
            # - recu: all recipients have
            agg = ParticipationConversation.objects.filter(conversation_id=conv_id).exclude(
                profile_id=msg.expediteur_id
            ).aggregate(
                total=Count("id"),
                read=Count("id", filter=Q(last_read_at__gte=msg.date_envoi)),
            )
            total = agg.get("total") or 0
            read = agg.get("read") or 0
            if total <= 0:
                lecture_statut = "recu"
            elif read >= total:
                lecture_statut = "recu"
            elif read > 0:
                lecture_statut = "recu_partiel"
            else:
                lecture_statut = "envoye"
            return (str(msg.id), profile.id, lecture_statut)
        except Profile.DoesNotExist:
            return None

    @database_sync_to_async
    def _get_profile_id(self, user_id):
        from .models import Profile
        profile = Profile.objects.filter(user_id=user_id).only("id").first()
        return profile.id if profile else None


class InboxConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        profile_id = await self._get_profile_id(self.user.id)
        if not profile_id:
            await self.close()
            return
        self.profile_id = str(profile_id)
        self.group_name = f"inbox_{self.profile_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Inbox consumer is server-push only for now.
        return

    async def inbox_update_v1(self, event):
        await self.send(text_data=json.dumps(event))

    async def unread_count_v1(self, event):
        await self.send(text_data=json.dumps(event))

    async def task_update_v1(self, event):
        await self.send(text_data=json.dumps(event))

    async def milestone_update_v1(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def _get_profile_id(self, user_id):
        from .models import Profile
        profile = Profile.objects.filter(user_id=user_id).only("id").first()
        return profile.id if profile else None
