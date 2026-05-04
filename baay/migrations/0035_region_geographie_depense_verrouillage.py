# Generated manually — Régions pan-africaines (schéma) + verrouillage fiches Depense.

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("baay", "0034_projet_agronomie_blank"),
    ]

    operations = [
        migrations.CreateModel(
            name="Region",
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
                ("nom", models.CharField(max_length=150)),
                (
                    "code",
                    models.CharField(
                        blank=True,
                        help_text="Code officiel facultatif (ex. ISO subdivisions).",
                        max_length=32,
                    ),
                ),
                (
                    "pays",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="regions",
                        to="baay.pays",
                    ),
                ),
            ],
            options={
                "verbose_name": "Région",
                "verbose_name_plural": "Régions",
                "ordering": ["pays__nom", "nom"],
            },
        ),
        migrations.AddConstraint(
            model_name="region",
            constraint=models.UniqueConstraint(
                fields=("pays", "nom"), name="uniq_region_nom_par_pays"
            ),
        ),
        migrations.AddField(
            model_name="depense",
            name="date_verrouillage",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="depense",
            name="verrouille",
            field=models.BooleanField(
                default=False,
                help_text="Verrouillage après clôture comptable : la ligne ne peut plus être modifiée.",
            ),
        ),
        migrations.AddField(
            model_name="localite",
            name="region",
            field=models.ForeignKey(
                blank=True,
                help_text="Rattache la localité pour des filtres cartographiques / agrégations régionales.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="localites",
                to="baay.region",
            ),
        ),
        migrations.AddField(
            model_name="ferme",
            name="region",
            field=models.ForeignKey(
                blank=True,
                help_text="Division administrative (filtre performances / cartes).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="fermes",
                to="baay.region",
            ),
        ),
    ]
