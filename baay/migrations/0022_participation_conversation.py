"""
Foundation migration: introduce ParticipationConversation as the through-model
for Conversation.participants, backfilling existing M2M rows.

Strategy:
1. CreateModel ParticipationConversation (new table baay_participationconversation).
2. RunPython data migration: copy rows from the auto-generated M2M table into
   the new through table, with joined_at = conversation.dernier_message as a
   reasonable default.
3. SeparateDatabaseAndState AlterField on Conversation.participants:
   - State: switch to through='ParticipationConversation' (Django state model
     now reflects the custom through).
   - Database: drop the old auto-generated table baay_conversation_participants,
     since the through-backed M2M now reads/writes baay_participationconversation.

All extra fields (last_read_at, pinned_at, archived_at, muted_until) are
nullable so existing `conversation.participants.add(profile, ...)` calls keep
working without rewriting any code.
"""

from django.db import migrations, models
import django.db.models.deletion


def backfill_participations(apps, schema_editor):
    Conversation = apps.get_model('baay', 'Conversation')
    ParticipationConversation = apps.get_model('baay', 'ParticipationConversation')
    # At this point Conversation.participants.through still refers to the
    # auto-generated through model that backs baay_conversation_participants.
    AutoThrough = Conversation.participants.through
    db = schema_editor.connection.alias

    rows = AutoThrough.objects.using(db).all().values('conversation_id', 'profile_id')
    to_create = []
    seen = set()
    # Map conversation_id -> dernier_message for joined_at default
    conv_dates = dict(
        Conversation.objects.using(db).values_list('id', 'dernier_message')
    )
    for row in rows:
        key = (row['conversation_id'], row['profile_id'])
        if key in seen:
            continue
        seen.add(key)
        to_create.append(ParticipationConversation(
            conversation_id=row['conversation_id'],
            profile_id=row['profile_id'],
            joined_at=conv_dates.get(row['conversation_id']),
        ))
    if to_create:
        ParticipationConversation.objects.using(db).bulk_create(
            to_create, ignore_conflicts=True
        )


def reverse_backfill(apps, schema_editor):
    # No-op: the participation table will be dropped by reversing CreateModel,
    # and the auto-M2M table will be recreated by reversing AlterField.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0021_message_client_message_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='ParticipationConversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('last_read_at', models.DateTimeField(blank=True, null=True)),
                ('pinned_at', models.DateTimeField(blank=True, null=True)),
                ('archived_at', models.DateTimeField(blank=True, null=True)),
                ('muted_until', models.DateTimeField(blank=True, null=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participations', to='baay.conversation')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participations', to='baay.profile')),
            ],
            options={
                'unique_together': {('profile', 'conversation')},
                'indexes': [
                    models.Index(fields=['profile', 'pinned_at'], name='baay_partic_profile_d54baa_idx'),
                    models.Index(fields=['profile', 'archived_at'], name='baay_partic_profile_61361f_idx'),
                ],
            },
        ),
        migrations.RunPython(backfill_participations, reverse_backfill),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='conversation',
                    name='participants',
                    field=models.ManyToManyField(
                        related_name='conversations',
                        through='baay.ParticipationConversation',
                        to='baay.profile',
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql='DROP TABLE IF EXISTS baay_conversation_participants;',
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
