# Generated migration for Andd Baay V2 - Pilier 3: Finance & ROI

import uuid
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration V2 - Pilier 3: Gestion Financière & ROI
    - Workflow validation recettes (statut, validation, refus)
    - Modèle SimulationROI pour scénarios prévisionnels
    """

    dependencies = [
        ("baay", "0039_recommandations_incidents_documents_ia"),
    ]

    operations = [
        # =========================================================================
        # Workflow Validation Recettes
        # =========================================================================
        migrations.AddField(
            model_name="recette",
            name="commentaire_validation",
            field=models.TextField(
                blank=True,
                help_text="Commentaire du validateur (en cas de refus ou validation)",
            ),
        ),
        migrations.AddField(
            model_name="recette",
            name="date_validation",
            field=models.DateTimeField(
                blank=True,
                help_text="Date de validation/refus",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="recette",
            name="statut_validation",
            field=models.CharField(
                choices=[
                    ("en_attente", "En attente de validation"),
                    ("validee", "Validée"),
                    ("refusee", "Refusée"),
                ],
                default="en_attente",
                help_text="Statut de validation par le manager de la ferme",
                max_length=15,
            ),
        ),
        migrations.AddField(
            model_name="recette",
            name="validee_par",
            field=models.ForeignKey(
                blank=True,
                help_text="Manager ayant validé la recette",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="recettes_validees",
                to="baay.profile",
            ),
        ),
        migrations.AddIndex(
            model_name="recette",
            index=models.Index(
                fields=["statut_validation", "-date_creation"],
                name="baay_recett_statut__5f8a1b_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="recette",
            index=models.Index(
                fields=["projet", "statut_validation"],
                name="baay_recett_projet__8c9d2e_idx",
            ),
        ),

        # =========================================================================
        # SimulationROI Model
        # =========================================================================
        migrations.CreateModel(
            name="SimulationROI",
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
                    "scenario_type",
                    models.CharField(
                        choices=[
                            ("optimiste", "Optimiste"),
                            ("realiste", "Réaliste"),
                            ("pessimiste", "Pessimiste"),
                            ("personnalise", "Personnalisé"),
                        ],
                        default="realiste",
                        help_text="Type de scénario simulé",
                        max_length=15,
                    ),
                ),
                (
                    "nom_simulation",
                    models.CharField(
                        blank=True,
                        help_text="Nom personnalisé (ex: 'Scenario prix haut')",
                        max_length=100,
                    ),
                ),
                (
                    "rendement_prevu_kg_ha",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Rendement prévisionnel (kg/hectare)",
                        max_digits=12,
                    ),
                ),
                (
                    "prix_prevu_fcfa_kg",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Prix prévisionnel (FCFA/kg)",
                        max_digits=12,
                    ),
                ),
                (
                    "investissement_prevu",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Investissement prévisionnel total (FCFA)",
                        max_digits=14,
                    ),
                ),
                (
                    "recette_prevue",
                    models.DecimalField(
                        decimal_places=2,
                        editable=False,
                        help_text="Recette prévisionnelle calculée",
                        max_digits=14,
                    ),
                ),
                (
                    "benefice_prevu",
                    models.DecimalField(
                        decimal_places=2,
                        editable=False,
                        help_text="Bénéfice net prévisionnel",
                        max_digits=14,
                    ),
                ),
                (
                    "roi_calcule_pct",
                    models.DecimalField(
                        decimal_places=2,
                        editable=False,
                        help_text="ROI prévisionnel en pourcentage",
                        max_digits=6,
                    ),
                ),
                (
                    "recette_reelle",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Recette réalisée (pour comparaison)",
                        max_digits=14,
                        null=True,
                    ),
                ),
                (
                    "ecart_reel_pct",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Écart réel vs prévision en %",
                        max_digits=6,
                        null=True,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Notes et hypothèses de la simulation",
                    ),
                ),
                ("date_simulation", models.DateTimeField(auto_now_add=True)),
                ("date_modification", models.DateTimeField(auto_now=True)),
                (
                    "cree_par",
                    models.ForeignKey(
                        help_text="Utilisateur ayant créé la simulation",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="simulations_roi_creees",
                        to="baay.profile",
                    ),
                ),
                (
                    "projet",
                    models.ForeignKey(
                        help_text="Projet concerné par la simulation",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="simulations_roi",
                        to="baay.projet",
                    ),
                ),
                (
                    "projet_produit",
                    models.ForeignKey(
                        blank=True,
                        help_text="Culture spécifique (optionnel)",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="simulations_roi",
                        to="baay.projetproduit",
                    ),
                ),
            ],
            options={
                "verbose_name": "Simulation ROI",
                "verbose_name_plural": "Simulations ROI",
                "ordering": ["-date_simulation"],
            },
        ),
        migrations.AddIndex(
            model_name="simulationroi",
            index=models.Index(
                fields=["projet", "scenario_type"],
                name="baay_simula_projet__3d4e5f_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="simulationroi",
            index=models.Index(
                fields=["cree_par", "-date_simulation"],
                name="baay_simula_cree_pa_6g7h8i_idx",
            ),
        ),
    ]
