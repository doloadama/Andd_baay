from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0020_message_reply_to_piece_jointe_reaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='client_message_id',
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
        migrations.AddConstraint(
            model_name='message',
            constraint=models.UniqueConstraint(
                condition=models.Q(client_message_id__isnull=False),
                fields=('conversation', 'expediteur', 'client_message_id'),
                name='uniq_message_client_id_per_sender_conversation',
            ),
        ),
    ]
