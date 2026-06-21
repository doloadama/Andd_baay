"""
Backfill : alimente l'inventaire de récoltes pour les projets déjà terminés.

Les rendements finaux saisis avant l'ajout de la synchronisation automatique
n'avaient jamais créé de StockRecolte. Cette commande rejoue la synchronisation
pour tous les projets « fini » / « cloturé ». Idempotente : relançable sans
créer de doublons.

Usage :
    python manage.py backfill_recoltes_inventaire            # applique
    python manage.py backfill_recoltes_inventaire --dry-run  # simulation
"""

from django.core.management.base import BaseCommand

from baay.models import Projet
from baay.services.inventory_service import synchroniser_recoltes_projet


class Command(BaseCommand):
    help = "Crée les stocks de récolte manquants pour les projets déjà terminés."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche ce qui serait créé sans rien écrire.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        statuts_fin = Projet.statuts_fin_activite()
        projets = (
            Projet.objects.filter(statut__in=statuts_fin)
            .select_related("ferme")
            .prefetch_related("projet_produits__produit")
        )

        total_projets = 0
        total_stocks = 0

        for projet in projets:
            produits_recoltes = [
                pp
                for pp in projet.projet_produits.all()
                if pp.rendement_final and pp.rendement_final > 0
            ]
            if not produits_recoltes:
                continue

            total_projets += 1
            if dry_run:
                for pp in produits_recoltes:
                    self.stdout.write(
                        f"[dry-run] {projet.nom} -> {pp.produit.nom} : "
                        f"{pp.rendement_final} kg"
                    )
                    total_stocks += 1
                continue

            stocks = synchroniser_recoltes_projet(projet)
            total_stocks += len(stocks)
            self.stdout.write(
                f"{projet.nom} : {len(stocks)} stock(s) de récolte synchronisé(s)."
            )

        prefixe = "[dry-run] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefixe}{total_projets} projet(s) traité(s), "
                f"{total_stocks} stock(s) de récolte."
            )
        )
