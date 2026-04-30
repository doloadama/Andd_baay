import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


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
        data = json.loads(text_data)
        msg_type = data.get('type')
        if msg_type == 'typing':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_typing',
                    'sender_id': self.user.id,
                    'sender_username': self.user.username,
                }
            )
        elif msg_type == 'stop_typing':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_stop_typing',
                    'sender_id': self.user.id,
                }
            )
        elif msg_type == 'read_receipt':
            message_id = data.get('message_id')
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_read_receipt',
                    'message_id': message_id,
                    'reader_id': self.user.id,
                }
            )

    async def chat_message(self, event):
        """Broadcast a new message to the group."""
        await self.send(text_data=json.dumps(event))

    async def chat_typing(self, event):
        """Someone is typing."""
        await self.send(text_data=json.dumps(event))

    async def chat_stop_typing(self, event):
        """Someone stopped typing."""
        await self.send(text_data=json.dumps(event))

    async def chat_read_receipt(self, event):
        """Someone read a message."""
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def _check_participation(self, conv_id, user_id):
        from .models import Conversation, Profile
        try:
            profile = Profile.objects.get(user_id=user_id)
            return Conversation.objects.filter(id=conv_id, participants=profile).exists()
        except Profile.DoesNotExist:
            return False
