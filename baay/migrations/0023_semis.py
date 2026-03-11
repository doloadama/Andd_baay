# Generated migration for Semis model

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0022_photoproduitagricole'),
    ]

    operations = [
        migrations.CreateModel(
            name='Semis',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('quantite_semences', models.DecimalField(decimal_places=2, help_text='Quantité de semences en kg', max_digits=10)),
                ('superficie_semee', models.DecimalField(decimal_places=2, help_text='Superficie semée en hectares', max_digits=10)),
                ('date_semis', models.DateField(help_text='Date du semis')),
                ('date_recolte_prevue', models.DateField(blank=True, help_text='Date de récolte prévue', null=True)),
                ('date_recolte_effective', models.DateField(blank=True, help_text='Date de récolte effective', null=True)),
                ('statut', models.CharField(choices=[('planifie', 'Planifié'), ('seme', 'Semé'), ('en_croissance', 'En croissance'), ('recolte', 'Récolté'), ('echec', 'Échec')], default='planifie', max_length=20)),
                ('notes', models.TextField(blank=True, help_text='Notes et observations', null=True)),
                ('rendement_obtenu', models.DecimalField(blank=True, decimal_places=2, help_text='Rendement obtenu en kg', max_digits=10, null=True)),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('date_modification', models.DateTimeField(auto_now=True)),
                ('culture', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='semis', to='baay.produitagricole')),
                ('projet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='semis', to='baay.projet')),
                ('utilisateur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='semis', to='baay.profile')),
            ],
            options={
                'verbose_name': 'Semis',
                'verbose_name_plural': 'Semis',
                'ordering': ['-date_semis'],
            },
        ),
    ]
