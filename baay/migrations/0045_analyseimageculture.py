# Generated manually for BaayVision integration

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("baay", "0044_projet_type_cycle_campagneprojet"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnalyseImageCulture",
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
                    "type_analyse",
                    models.CharField(
                        choices=[("PLANT_PEST", "Plante / ravageur (photo rapprochée)")],
                        default="PLANT_PEST",
                        max_length=32,
                    ),
                ),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("en_attente", "En attente"),
                            ("en_cours", "En cours"),
                            ("terminee", "Terminée"),
                            ("echec", "Échec"),
                        ],
                        db_index=True,
                        default="en_attente",
                        max_length=16,
                    ),
                ),
                ("image_hash", models.CharField(blank=True, db_index=True, max_length=64)),
                ("resultat", models.JSONField(blank=True, null=True)),
                ("sujet_type", models.CharField(blank=True, max_length=32)),
                ("sujet_description", models.TextField(blank=True)),
                ("message_erreur", models.TextField(blank=True)),
                ("date_creation", models.DateTimeField(auto_now_add=True)),
                ("date_fin", models.DateTimeField(blank=True, null=True)),
                (
                    "demandee_par",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="analyses_image_demandees",
                        to="baay.profile",
                    ),
                ),
                (
                    "projet_produit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analyses_image",
                        to="baay.projetproduit",
                    ),
                ),
            ],
            options={
                "verbose_name": "Analyse image culture",
                "verbose_name_plural": "Analyses image culture",
                "ordering": ["-date_creation"],
                "indexes": [
                    models.Index(
                        fields=["projet_produit", "-date_creation"],
                        name="baay_analys_projet__a1b2c3_idx",
                    ),
                ],
            },
        ),
    ]
