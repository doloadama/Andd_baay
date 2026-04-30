# Generated manually for Conversation and Message models

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('baay', '0018_rename_baay_tache_ferme_i_idx_baay_tache_ferme_i_e4cbc7_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('sujet', models.CharField(blank=True, max_length=200)),
                ('dernier_message', models.DateTimeField(auto_now=True)),
                ('ferme', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='baay.ferme')),
                ('participants', models.ManyToManyField(related_name='conversations', to='baay.profile')),
            ],
            options={
                'ordering': ['-dernier_message'],
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('contenu', models.TextField()),
                ('date_envoi', models.DateTimeField(auto_now_add=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='baay.conversation')),
                ('expediteur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages_envoyes', to='baay.profile')),
                ('lu_par', models.ManyToManyField(blank=True, related_name='messages_lus', to='baay.profile')),
            ],
            options={
                'ordering': ['date_envoi'],
            },
        ),
    ]
