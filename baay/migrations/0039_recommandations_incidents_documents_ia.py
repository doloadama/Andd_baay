# Generated migration for Andd Baay V2 - IA Agronomique

import uuid
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration V2 - Pilier 1: IA & Intelligence Agronomique
    - RecommandationFertilisation: Conseils fertilisation basés N-P-K
    - IncidentRapporte: Signalement vocal hands-free
    - DocumentConnaissance: Base RAG pour assistant IA
    """

    dependencies = [
        ("baay", "0038_rename_baay_histor_ferme_i_date_idx_baay_histor_ferme_i_fa5e7d_idx_and_more"),
    ]

    operations = [
        # =========================================================================
        # RecommandationFertilisation
        # =========================================================================
        migrations.CreateModel(
            name="RecommandationFertilisation",
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
                    "type_engrais_conseille",
                    models.CharField(
                        choices=[
                            ("organique", "Organique (Compost, Fumier)"),
                            ("mineral_npk", "Minéral NPK"),
                            ("mineral_uree", "Minéral (Urée)"),
                            ("mixte", "Mixte (Organique + Minéral)"),
                            ("aucun", "Aucun - Sol équilibré"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "quantite_kg_ha",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Quantité recommandée en kg par hectare",
                        max_digits=8,
                        null=True,
                    ),
                ),
                (
                    "message_explication",
                    models.TextField(
                        help_text="Explication détaillée de la recommandation (raisonnement IA)"
                    ),
                ),
                (
                    "priorite_actions",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Liste d'actions prioritaires [{'action': '...', 'urgence': 'haute|moyenne|basse'}]",
                    ),
                ),
                (
                    "confiance_score",
                    models.DecimalField(
                        decimal_places=2,
                        default=0.75,
                        help_text="Score de confiance de la recommandation (0.0 - 1.0)",
                        max_digits=4,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(1),
                        ],
                    ),
                ),
                ("date_creation", models.DateTimeField(auto_now_add=True)),
                ("date_modification", models.DateTimeField(auto_now=True)),
                (
                    "vue_par_utilisateur",
                    models.DateTimeField(
                        blank=True,
                        help_text="Date de consultation par l'utilisateur",
                        null=True,
                    ),
                ),
                (
                    "culture_cible",
                    models.ForeignKey(
                        blank=True,
                        help_text="Culture pour laquelle la recommandation est faite",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="recommandations_fertilisation",
                        to="baay.produitagricole",
                    ),
                ),
                (
                    "historique_sol",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recommandations",
                        to="baay.historiquesol",
                    ),
                ),
            ],
            options={
                "verbose_name": "Recommandation Fertilisation",
                "verbose_name_plural": "Recommandations Fertilisation",
                "ordering": ["-date_creation"],
            },
        ),
        migrations.AddIndex(
            model_name="recommandationfertilisation",
            index=models.Index(
                fields=["historique_sol", "-date_creation"],
                name="baay_recomm_histor_7d9c2a_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="recommandationfertilisation",
            index=models.Index(
                fields=["culture_cible", "-confiance_score"],
                name="baay_recomm_culture_9e8b1c_idx",
            ),
        ),

        # =========================================================================
        # IncidentRapporte
        # =========================================================================
        migrations.CreateModel(
            name="IncidentRapporte",
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
                    "type_incident",
                    models.CharField(
                        choices=[
                            ("invasion_ravageurs", "Invasion de ravageurs (criquets, chenilles...)"),
                            ("maladie_feuilles", "Maladie des feuilles"),
                            ("maladie_racines", "Maladie des racines/tiges"),
                            ("stress_hydrique", "Stress hydrique / Sécheresse"),
                            ("inondation", "Inondation / Excès d'eau"),
                            ("vol", "Vol / Intrusion"),
                            ("incident_materiel", "Incident matériel / Dégâts"),
                            ("autre", "Autre incident"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "gravite_detectee",
                    models.CharField(
                        choices=[
                            ("faible", "Faible - À surveiller"),
                            ("moyenne", "Moyenne - Action nécessaire"),
                            ("haute", "Haute - Urgent"),
                            ("critique", "Critique - Danger immédiat"),
                        ],
                        default="moyenne",
                        max_length=10,
                    ),
                ),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("signale", "Signalé - Non traité"),
                            ("en_cours", "Traitement en cours"),
                            ("resolu", "Résolu"),
                            ("escalade", "Escaladé au manager"),
                        ],
                        default="signale",
                        max_length=15,
                    ),
                ),
                (
                    "transcription_audio",
                    models.TextField(
                        help_text="Texte transcrit de l'audio de signalement"
                    ),
                ),
                (
                    "audio_url",
                    models.URLField(
                        blank=True,
                        help_text="URL du fichier audio stocké (Cloudinary ou autre)",
                        null=True,
                    ),
                ),
                (
                    "localisation_gps_lat",
                    models.FloatField(
                        blank=True,
                        help_text="Latitude GPS au moment du signalement",
                        null=True,
                    ),
                ),
                (
                    "localisation_gps_lon",
                    models.FloatField(
                        blank=True,
                        help_text="Longitude GPS au moment du signalement",
                        null=True,
                    ),
                ),
                (
                    "parcelle_concernee",
                    models.CharField(
                        blank=True,
                        help_text="Nom de la parcelle si mentionnée",
                        max_length=100,
                    ),
                ),
                ("date_signalement", models.DateTimeField(auto_now_add=True)),
                (
                    "date_traitement",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("commentaire_resolution", models.TextField(blank=True)),
                (
                    "ferme",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="incidents",
                        to="baay.ferme",
                    ),
                ),
                (
                    "signale_par",
                    models.ForeignKey(
                        help_text="Utilisateur qui a signalé l'incident",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="incidents_signales",
                        to="baay.profile",
                    ),
                ),
                (
                    "traite_par",
                    models.ForeignKey(
                        blank=True,
                        help_text="Responsable ayant pris en charge l'incident",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="incidents_traites",
                        to="baay.profile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Incident Rapporté",
                "verbose_name_plural": "Incidents Rapportés",
                "ordering": ["-date_signalement"],
            },
        ),
        migrations.AddIndex(
            model_name="incidentrapporte",
            index=models.Index(
                fields=["ferme", "statut"],
                name="baay_inciden_ferme_i_8f3d2e_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="incidentrapporte",
            index=models.Index(
                fields=["type_incident", "-date_signalement"],
                name="baay_inciden_type_in_5e7a9b_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="incidentrapporte",
            index=models.Index(
                fields=["signale_par", "-date_signalement"],
                name="baay_inciden_signale_e2f1c8_idx",
            ),
        ),

        # =========================================================================
        # DocumentConnaissance (RAG)
        # =========================================================================
        migrations.CreateModel(
            name="DocumentConnaissance",
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
                ("titre", models.CharField(max_length=200)),
                (
                    "contenu",
                    models.TextField(help_text="Contenu textuel complet du document"),
                ),
                (
                    "categorie",
                    models.CharField(
                        choices=[
                            ("culture", "Culture / Semis / Récolte"),
                            ("fertilisation", "Fertilisation / Sol"),
                            ("irrigation", "Irrigation / Eau"),
                            ("ravageurs", "Ravageurs / Maladies"),
                            ("climat", "Climat / Météo"),
                            ("economie", "Économie / Marché"),
                            ("pratiques", "Pratiques paysannes"),
                            ("reglementation", "Réglementation / Certif"),
                            ("autre", "Autre"),
                        ],
                        default="autre",
                        max_length=20,
                    ),
                ),
                (
                    "mots_cles",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Liste de mots-clés pour recherche",
                    ),
                ),
                (
                    "source_url",
                    models.URLField(
                        blank=True,
                        help_text="URL source si document externe",
                        null=True,
                    ),
                ),
                (
                    "auteur",
                    models.CharField(
                        blank=True,
                        help_text="Auteur ou organisation source",
                        max_length=100,
                    ),
                ),
                (
                    "embedding_status",
                    models.CharField(
                        choices=[
                            ("pending", "En attente"),
                            ("indexed", "Indexé"),
                            ("failed", "Échec"),
                        ],
                        default="pending",
                        help_text="Statut de l'indexation vectorielle",
                        max_length=15,
                    ),
                ),
                (
                    "date_indexation",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("is_actif", models.BooleanField(default=True)),
                ("date_creation", models.DateTimeField(auto_now_add=True)),
                ("date_modification", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Document de Connaissance",
                "verbose_name_plural": "Documents de Connaissance",
                "ordering": ["-date_creation"],
            },
        ),
        migrations.AddIndex(
            model_name="documentconnaissance",
            index=models.Index(
                fields=["categorie", "is_actif"],
                name="baay_documen_categor_a1b2c3_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="documentconnaissance",
            index=models.Index(
                fields=["mots_cles"],
                name="baay_documen_mots_cl_d4e5f6_idx",
            ),
        ),
    ]
