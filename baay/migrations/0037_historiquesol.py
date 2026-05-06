import uuid
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("baay", "0036_cloudinary_media_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="HistoriqueSol",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "parcelle_nom",
                    models.CharField(
                        blank=True,
                        help_text="Nom libre de la parcelle ou zone (ex. 'Parcelle Nord', 'Champ A').",
                        max_length=100,
                    ),
                ),
                (
                    "date_mesure",
                    models.DateField(
                        help_text="Date du prélèvement / analyse de sol."
                    ),
                ),
                (
                    "ph",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="pH du sol (0–14). Idéal cultures : 5.5–7.0.",
                        max_digits=4,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(14),
                        ],
                    ),
                ),
                (
                    "azote_ppm",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Teneur en azote (N) en ppm.",
                        max_digits=8,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "phosphore_ppm",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Teneur en phosphore (P) en ppm.",
                        max_digits=8,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "potassium_ppm",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Teneur en potassium (K) en ppm.",
                        max_digits=8,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Observations agronomiques libres.",
                    ),
                ),
                (
                    "date_creation",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "culture_precedente",
                    models.ForeignKey(
                        blank=True,
                        help_text="Culture cultivée lors du cycle précédent (rotation).",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="historiques_sol_precedents",
                        to="baay.produitagricole",
                    ),
                ),
                (
                    "ferme",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="historiques_sol",
                        to="baay.ferme",
                    ),
                ),
            ],
            options={
                "verbose_name": "Historique Sol",
                "verbose_name_plural": "Historiques Sol",
                "ordering": ["-date_mesure"],
            },
        ),
        migrations.AddIndex(
            model_name="historiquesol",
            index=models.Index(
                fields=["ferme", "-date_mesure"],
                name="baay_histor_ferme_i_date_idx",
            ),
        ),
    ]
