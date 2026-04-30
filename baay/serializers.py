from rest_framework import serializers
from .models import Conversation, Ferme, Message, MessageReaction, Projet


class ProjetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projet
        fields = '__all__'


class FermeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ferme
        fields = ['id', 'nom', 'description', 'code_acces', 'date_creation']


class ConversationSerializer(serializers.ModelSerializer):
    participants_count = serializers.IntegerField(source='participants.count', read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'sujet', 'ferme', 'dernier_message', 'participants_count']


class MessageSerializer(serializers.ModelSerializer):
    expediteur_nom = serializers.CharField(source='expediteur.user.username', read_only=True)
    is_lu_par_tous = serializers.BooleanField(read_only=True)
    client_message_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Message
        fields = [
            'id',
            'client_message_id',
            'conversation',
            'expediteur',
            'expediteur_nom',
            'contenu',
            'date_envoi',
            'piece_jointe',
            'reply_to',
            'is_lu_par_tous',
        ]


class MessageReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageReaction
        fields = ['id', 'message', 'utilisateur', 'emoji', 'date_ajout']


class MessageEventV1Serializer(serializers.Serializer):
    type = serializers.CharField()
    event_version = serializers.CharField()
    event_id = serializers.CharField()
    message_id = serializers.UUIDField()
    client_message_id = serializers.UUIDField(allow_null=True, required=False)
    sender_id = serializers.UUIDField()
    sender_username = serializers.CharField()
    sender_name = serializers.CharField()
    contenu = serializers.CharField(allow_blank=True)
    date_envoi = serializers.CharField()
    date_envoi_iso = serializers.DateTimeField()
    conversation_id = serializers.UUIDField()
    reply_to_id = serializers.UUIDField(allow_null=True, required=False)
    reply_preview = serializers.CharField(allow_null=True, required=False)
    piece_jointe_url = serializers.CharField(allow_null=True, required=False)
    piece_jointe_name = serializers.CharField(allow_null=True, required=False)
    is_lu_par_tous = serializers.BooleanField(required=False)