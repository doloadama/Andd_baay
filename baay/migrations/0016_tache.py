import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0015_alter_membreferme_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tache',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('titre', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('priorite', models.CharField(
                    choices=[('basse', 'Basse'), ('normale', 'Normale'), ('haute', 'Haute'), ('urgente', 'Urgente')],
                    default='normale', max_length=10)),
                ('statut', models.CharField(
                    choices=[('a_faire', 'À faire'), ('en_cours', 'En cours'),
                             ('terminee', 'Terminée'), ('annulee', 'Annulée')],
                    default='a_faire', max_length=10)),
                ('date_echeance', models.DateField(blank=True, null=True)),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('date_modification', models.DateTimeField(auto_now=True)),
                ('date_terminee', models.DateTimeField(blank=True, null=True)),
                ('commentaire_retour', models.TextField(
                    blank=True,
                    help_text="Commentaire laissé par l'assigné lors de la mise à jour.")),
                ('assigne_a', models.ForeignKey(
                    help_text='Membre à qui la tâche est assignée.',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='taches_recues', to='baay.profile')),
                ('assigne_par', models.ForeignKey(
                    help_text='Auteur de la tâche.', null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='taches_creees', to='baay.profile')),
                ('ferme', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='taches', to='baay.ferme')),
                ('projet', models.ForeignKey(
                    blank=True, null=True,
                    help_text='Projet concerné par la tâche (optionnel).',
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='taches', to='baay.projet')),
            ],
            options={
                'ordering': ['-date_creation'],
            },
        ),
        migrations.AddIndex(
            model_name='tache',
            index=models.Index(fields=['ferme', 'statut'], name='baay_tache_ferme_i_idx'),
        ),
        migrations.AddIndex(
            model_name='tache',
            index=models.Index(fields=['assigne_a', 'statut'], name='baay_tache_assigne_idx'),
        ),
    ]
