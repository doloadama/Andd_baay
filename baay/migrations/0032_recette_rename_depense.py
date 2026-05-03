# Generated manually

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import uuid
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("baay", "0031_investissement_verrouille"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="recette",
            name="baay_recett_projet__5d6eb7_idx",
        ),
        migrations.RenameField(
            model_name="recette",
            old_name="produit_vendu",
            new_name="produit",
        ),
        migrations.RenameField(
            model_name="recette",
            old_name="quantite_vendue",
            new_name="quantite",
        ),
        migrations.RenameField(
            model_name="recette",
            old_name="date_encaissement",
            new_name="date_vente",
        ),
        migrations.AlterModelOptions(
            name="recette",
            options={"ordering": ["-date_vente", "-date_creation"]},
        ),
        migrations.AddIndex(
            model_name="recette",
            index=models.Index(fields=["projet", "date_vente"], name="baay_recett_projet__dv_idx"),
        ),
        migrations.CreateModel(
            name="Depense",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("libelle", models.CharField(max_length=255)),
                (
                    "montant",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                    ),
                ),
                ("date_depense", models.DateField(default=django.utils.timezone.now)),
                ("description", models.TextField(blank=True)),
                (
                    "projet",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="depenses",
                        to="baay.projet",
                    ),
                ),
            ],
            options={
                "verbose_name": "Dépense",
                "verbose_name_plural": "Dépenses",
                "ordering": ["-date_depense", "-pk"],
            },
        ),
    ]
