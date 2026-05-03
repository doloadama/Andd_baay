import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("baay", "0032_recette_rename_depense"),
    ]

    operations = [
        migrations.AlterField(
            model_name="projet",
            name="date_fin",
            field=models.DateField(
                blank=True,
                help_text="Date de fin prévue ou de clôture opérationnelle du projet (avec la date de "
                "lancement, sert au calcul du taux d'avancement par défaut).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="projet",
            name="taux_avancement_personnalise",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Remplace le calcul automatique (dates début / fin). Réservé au manager de la "
                "ferme et aux administrateurs.",
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100),
                ],
            ),
        ),
    ]
