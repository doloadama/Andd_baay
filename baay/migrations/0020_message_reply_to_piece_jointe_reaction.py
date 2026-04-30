# Generated manually for Phase 2 UX Polish: reply_to, piece_jointe, MessageReaction, indexes

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('baay', '0019_conversation_message'),
    ]

    operations = [
        # Add reply_to and piece_jointe to Message
        migrations.AddField(
            model_name='message',
            name='reply_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reponses', to='baay.message'),
        ),
        migrations.AddField(
            model_name='message',
            name='piece_jointe',
            field=models.FileField(blank=True, null=True, upload_to='messages/%Y/%m/'),
        ),
        # Add indexes on Message
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['conversation', 'date_envoi'], name='baay_message_convers_d3c3e4_idx'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['expediteur', 'date_envoi'], name='baay_message_expedit_c3a5e4_idx'),
        ),
        # Create MessageReaction model
        migrations.CreateModel(
            name='MessageReaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emoji', models.CharField(max_length=8)),
                ('date_ajout', models.DateTimeField(auto_now_add=True)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='baay.message')),
                ('utilisateur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions_message', to='baay.profile')),
            ],
            options={
                'unique_together': {('message', 'utilisateur', 'emoji')},
            },
        ),
        # Add index on MessageReaction
        migrations.AddIndex(
            model_name='messagereaction',
            index=models.Index(fields=['message', 'emoji'], name='baay_messag_message_emoji_idx'),
        ),
    ]
