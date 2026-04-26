from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0013_ferme_code_acces_demandeaccesferme'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='demandeaccesferme',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='demandeaccesferme',
            constraint=models.UniqueConstraint(
                fields=['ferme', 'utilisateur'],
                condition=models.Q(statut='en_attente'),
                name='unique_demande_en_attente_par_ferme_utilisateur',
            ),
        ),
    ]
