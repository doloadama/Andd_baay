from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0049_previsionfeatures'),
    ]

    operations = [
        migrations.CreateModel(
            name='MLModeleInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('culture_slug', models.CharField(db_index=True, max_length=100)),
                ('culture_nom', models.CharField(max_length=100)),
                ('date_entrainement', models.DateTimeField(auto_now_add=True)),
                ('n_observations', models.IntegerField(help_text="Taille du dataset d'entraînement.")),
                ('r2_score', models.FloatField(blank=True, help_text='R\xb2 moyen en cross-validation.', null=True)),
                ('rmse', models.FloatField(blank=True, help_text='RMSE moyen en cross-validation (kg/ha).', null=True)),
                ('actif', models.BooleanField(default=True, help_text='True si ce modèle est actuellement utilisé en production.')),
                ('declencheur', models.CharField(
                    choices=[
                        ('manuel', 'Manuel (commande)'),
                        ('auto', 'Automatique (Beat hebdomadaire)'),
                        ('signal', 'Signal (nouvelle clôture)'),
                    ],
                    default='manuel',
                    max_length=20,
                )),
                ('warm_start', models.BooleanField(default=False, help_text='True si entraîné en warm-start sur le modèle précédent.')),
                ('fichier_pkl', models.CharField(help_text='Chemin absolu vers le fichier .pkl du modèle.', max_length=500)),
            ],
            options={
                'verbose_name': 'Modèle ML',
                'verbose_name_plural': 'Modèles ML',
                'ordering': ['-date_entrainement'],
            },
        ),
        migrations.AddIndex(
            model_name='mlmodeleinfo',
            index=models.Index(fields=['culture_slug', '-date_entrainement'], name='baay_mlmode_culture_date_idx'),
        ),
        migrations.AddIndex(
            model_name='mlmodeleinfo',
            index=models.Index(fields=['actif'], name='baay_mlmode_actif_idx'),
        ),
    ]
