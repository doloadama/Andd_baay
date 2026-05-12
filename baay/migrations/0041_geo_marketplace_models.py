# Generated migration for Andd Baay V2 - Pilier 4: Communauté & Géo-Data

import uuid
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration V2 - Pilier 4: Géo-Data et Marketplace
    - OffreProduit: Offres de surplus sur le marketplace
    - TransactionMarche: Transactions entre fermes
    """

    dependencies = [
        ("baay", "0040_workflow_finance_roi"),
    ]

    operations = [
        # =========================================================================
        # OffreProduit Model
        # =========================================================================
        migrations.CreateModel(
            name="OffreProduit",
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
                    "titre_annonce",
                    models.CharField(
                        help_text="Titre de l'annonce (ex: 'Mil blanc de qualité premium')",
                        max_length=200,
                    ),
                ),
                ("description", models.TextField(blank=True, help_text="Description détaillée du produit")),
                (
                    "quantite_disponible",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Quantité disponible (kg)",
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0.01)],
                    ),
                ),
                (
                    "unite",
                    models.CharField(
                        choices=[("kg", "Kilogramme"), ("tonne", "Tonne"), ("sac", "Sac (50kg)")],
                        default="kg",
                        max_length=10,
                    ),
                ),
                (
                    "prix_unitaire",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Prix unitaire (FCFA)",
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "prix_negociable",
                    models.BooleanField(default=True, help_text="Le prix est-il négociable ?"),
                ),
                (
                    "qualite",
                    models.CharField(
                        choices=[
                            ("A", "Qualité A - Premium"),
                            ("B", "Qualité B - Standard"),
                            ("C", "Qualité C - Acceptable"),
                        ],
                        default="B",
                        help_text="Qualité du produit",
                        max_length=1,
                    ),
                ),
                (
                    "date_recolte",
                    models.DateField(blank=True, help_text="Date de récolte (pour fraîcheur)", null=True),
                ),
                (
                    "certification_bio",
                    models.BooleanField(default=False, help_text="Produit certifié bio/organique"),
                ),
                (
                    "livraison_possible",
                    models.BooleanField(
                        default=False, help_text="Livraison possible (à définir avec acheteur)"
                    ),
                ),
                (
                    "frais_livraison",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Frais de livraison estimés (si applicable)",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("disponible", "Disponible"),
                            ("reserve", "Réservé"),
                            ("vendu", "Vendu"),
                            ("expire", "Expiré"),
                            ("annule", "Annulé"),
                        ],
                        default="disponible",
                        max_length=15,
                    ),
                ),
                (
                    "date_expiration",
                    models.DateField(help_text="Date d'expiration de l'offre"),
                ),
                ("photos", models.JSONField(blank=True, default=list, help_text="URLs des photos (Cloudinary)")),
                ("nb_vues", models.PositiveIntegerField(default=0)),
                ("nb_contacts", models.PositiveIntegerField(default=0)),
                ("date_creation", models.DateTimeField(auto_now_add=True)),
                ("date_modification", models.DateTimeField(auto_now=True)),
                (
                    "cree_par",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offres_creees",
                        to="baay.profile",
                    ),
                ),
                (
                    "localite_retrait",
                    models.ForeignKey(
                        blank=True,
                        help_text="Localité de retrait/livraison",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="offres_retrait",
                        to="baay.localite",
                    ),
                ),
                (
                    "produit",
                    models.ForeignKey(
                        help_text="Type de produit agricole",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offres_marketplace",
                        to="baay.produitagricole",
                    ),
                ),
                (
                    "vendeur",
                    models.ForeignKey(
                        help_text="Ferme vendeuse du produit",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offres",
                        to="baay.ferme",
                    ),
                ),
            ],
            options={
                "verbose_name": "Offre Produit",
                "verbose_name_plural": "Offres Produits",
                "ordering": ["-date_creation"],
            },
        ),
        migrations.AddIndex(
            model_name="offreproduit",
            index=models.Index(
                fields=["produit", "statut", "-date_creation"],
                name="baay_offrepr_produit_9f8a2b_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="offreproduit",
            index=models.Index(
                fields=["vendeur", "statut"],
                name="baay_offrepr_vendeur_5c7d3e_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="offreproduit",
            index=models.Index(
                fields=["localite_retrait", "statut"],
                name="baay_offrepr_localit_1e6b4c_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="offreproduit",
            index=models.Index(
                fields=["qualite", "prix_unitaire"],
                name="baay_offrepr_qualite_2d8e7f_idx",
            ),
        ),

        # =========================================================================
        # TransactionMarche Model
        # =========================================================================
        migrations.CreateModel(
            name="TransactionMarche",
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
                    "quantite_achetee",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Quantité finalement achetée",
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0.01)],
                    ),
                ),
                (
                    "prix_total",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Prix total de la transaction",
                        max_digits=14,
                    ),
                ),
                (
                    "prix_negocie_unitaire",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Prix unitaire négocié (si différent de l'offre)",
                        max_digits=12,
                        null=True,
                    ),
                ),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("en_negociation", "En négociation"),
                            ("confirme", "Confirmé"),
                            ("paye", "Payé"),
                            ("livre", "Livré"),
                            ("annule", "Annulé"),
                            ("litige", "Litige"),
                        ],
                        default="en_negociation",
                        max_length=15,
                    ),
                ),
                ("date_transaction", models.DateTimeField(auto_now_add=True)),
                (
                    "date_confirmation",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "date_paiement",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "date_livraison",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "mode_paiement",
                    models.CharField(blank=True, help_text="Mode de paiement utilisé", max_length=50),
                ),
                (
                    "reference_paiement",
                    models.CharField(
                        blank=True,
                        help_text="Référence de transaction (mobile money, virement...)",
                        max_length=100,
                    ),
                ),
                (
                    "lieu_retrait",
                    models.TextField(blank=True, help_text="Adresse ou lieu de retrait convenu"),
                ),
                ("note_vendeur", models.TextField(blank=True, help_text="Note du vendeur sur l'acheteur")),
                (
                    "note_acheteur",
                    models.TextField(blank=True, help_text="Note de l'acheteur sur le vendeur"),
                ),
                (
                    "rating_vendeur",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        help_text="Évaluation vendeur (1-5)",
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ],
                    ),
                ),
                (
                    "rating_acheteur",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        help_text="Évaluation acheteur (1-5)",
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ],
                    ),
                ),
                ("date_creation", models.DateTimeField(auto_now_add=True)),
                ("date_modification", models.DateTimeField(auto_now=True)),
                (
                    "acheteur",
                    models.ForeignKey(
                        help_text="Ferme acheteuse",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="achats",
                        to="baay.ferme",
                    ),
                ),
                (
                    "cree_par",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transactions_initiees",
                        to="baay.profile",
                    ),
                ),
                (
                    "offre",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transactions",
                        to="baay.offreproduit",
                    ),
                ),
            ],
            options={
                "verbose_name": "Transaction Marché",
                "verbose_name_plural": "Transactions Marché",
                "ordering": ["-date_creation"],
            },
        ),
        migrations.AddIndex(
            model_name="transactionmarche",
            index=models.Index(
                fields=["offre", "statut"],
                name="baay_transac_offre_i_4f7g8h_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="transactionmarche",
            index=models.Index(
                fields=["acheteur", "-date_creation"],
                name="baay_transac_acheteu_6i9j0k_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="transactionmarche",
            index=models.Index(
                fields=["statut", "-date_creation"],
                name="baay_transac_statut_8m1n2o_idx",
            ),
        ),
    ]
