import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0048_projetproduit_etat_vegetatif'),
    ]

    operations = [
        migrations.CreateModel(
            name='PrevisionFeatures',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'prevision',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='features',
                        to='baay.previsionrecolte',
                    ),
                ),
                (
                    'features',
                    models.JSONField(
                        default=dict,
                        help_text='Vecteur de features au moment de la prédiction (dict JSON).',
                    ),
                ),
                (
                    'rendement_reel',
                    models.FloatField(
                        blank=True,
                        null=True,
                        help_text='Rendement réel (kg) enregistré à la clôture du projet.',
                    ),
                ),
                (
                    'erreur_pct',
                    models.FloatField(
                        blank=True,
                        null=True,
                        help_text='Erreur relative en % : (mid_predit - reel) / reel * 100.',
                    ),
                ),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                (
                    'date_validation',
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="Date à laquelle le rendement réel a été enregistré (label ML).",
                    ),
                ),
            ],
            options={
                'verbose_name': 'Features de prévision',
                'verbose_name_plural': 'Features de prévisions',
            },
        ),
        migrations.AddIndex(
            model_name='previsionfeatures',
            index=models.Index(fields=['date_creation'], name='baay_prevfe_date_cr_idx'),
        ),
        migrations.AddIndex(
            model_name='previsionfeatures',
            index=models.Index(fields=['rendement_reel'], name='baay_prevfe_rendem_idx'),
        ),
    ]
