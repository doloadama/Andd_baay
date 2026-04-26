# Generated manually

import django.db.models.deletion
import uuid
import secrets
import string
from django.db import migrations, models


def generate_codes(apps, schema_editor):
    Ferme = apps.get_model('baay', 'Ferme')
    alphabet = string.ascii_uppercase + string.digits
    used = set(Ferme.objects.exclude(code_acces='').values_list('code_acces', flat=True))
    for ferme in Ferme.objects.filter(code_acces=''):
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(8))
            if code not in used:
                used.add(code)
                break
        ferme.code_acces = code
        ferme.save(update_fields=['code_acces'])


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0012_merge_20260425_2155'),
    ]

    operations = [
        migrations.AddField(
            model_name='ferme',
            name='code_acces',
            field=models.CharField(blank=True, max_length=12, default=''),
        ),
        migrations.RunPython(generate_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='ferme',
            name='code_acces',
            field=models.CharField(blank=True, max_length=12, unique=True),
        ),
        migrations.CreateModel(
            name='DemandeAccesFerme',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=12)),
                ('statut', models.CharField(choices=[('en_attente', 'En attente'), ('approuvee', 'Approuvée'), ('refusee', 'Refusée')], default='en_attente', max_length=20)),
                ('date_demande', models.DateTimeField(auto_now_add=True)),
                ('date_traitement', models.DateTimeField(blank=True, null=True)),
                ('ferme', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='demandes_acces', to='baay.ferme')),
                ('utilisateur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='demandes_acces_ferme', to='baay.profile')),
            ],
            options={
                'unique_together': {('ferme', 'utilisateur', 'statut')},
                'ordering': ['-date_demande'],
            },
        ),
    ]
