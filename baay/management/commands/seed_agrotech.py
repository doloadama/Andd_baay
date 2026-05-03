from django.core.management.base import BaseCommand
from baay.models import Localite, ProduitAgricole, HistoriqueRendement
import random
from decimal import Decimal

class Command(BaseCommand):
    help = 'Génère des données agricoles factices pour le Sénégal afin de faciliter le Machine Learning.'

    def handle(self, *args, **kwargs):
        self.stdout.write('Création des paramètres agricoles...')
        
        arachide, _ = ProduitAgricole.objects.get_or_create(
            nom="Arachide",
            defaults={
                'saison': 'Hivernage', 
                'prix_par_kg': 500,
                'rendement_moyen': 1100,
                # Saharan specifics
                'rendement_potentiel_max': 1800,
                'besoin_eau_mm': 550,
                'cycle_culture_jours': 110,
            }
        )
        riz, _ = ProduitAgricole.objects.get_or_create(
            nom="Riz",
            defaults={
                'saison': 'Contre-saison', 
                'prix_par_kg': 350,
                'rendement_moyen': 4500,
                'rendement_potentiel_max': 6500,
                'besoin_eau_mm': 900,
                'cycle_culture_jours': 120,
            }
        )

        # Ajout de quelques produits résistants à la chaleur (exemples)
        mil, _ = ProduitAgricole.objects.get_or_create(
            nom="Mil",
            defaults={
                'saison': 'Hivernage',
                'prix_par_kg': 250,
                'rendement_moyen': 1200,
                'rendement_potentiel_max': 2000,
                'besoin_eau_mm': 400,
                'cycle_culture_jours': 95,
            }
        )
        sorgho, _ = ProduitAgricole.objects.get_or_create(
            nom="Sorgho",
            defaults={
                'saison': 'Hivernage',
                'prix_par_kg': 220,
                'rendement_moyen': 1400,
                'rendement_potentiel_max': 2300,
                'besoin_eau_mm': 450,
                'cycle_culture_jours': 105,
            }
        )

        self.stdout.write('Création de localités modèles...')
        diourbel, _ = Localite.objects.get_or_create(
            nom="Diourbel",
            defaults={'type_sol': 'Dior', 'latitude': 14.655 + random.uniform(-0.05,0.05), 'longitude': -16.234 + random.uniform(-0.05,0.05)}
        )
        richard_toll, _ = Localite.objects.get_or_create(
            nom="Richard Toll",
            defaults={'type_sol': 'Deck', 'latitude': 16.462 + random.uniform(-0.05,0.05), 'longitude': -15.694 + random.uniform(-0.05,0.05)}
        )

        self.stdout.write('Génération de l\'historique de rendements (5 dernières années)...')
        for year in range(2019, 2024):
            # Diourbel - Arachide (Sol Dior = Bon rendement, mais dépend de la pluie)
            pluvio_diourbel = random.uniform(400, 650)
            rendement_arachide = 1200 * (pluvio_diourbel / 550) * random.uniform(0.9, 1.1)
            
            HistoriqueRendement.objects.update_or_create(
                localite=diourbel,
                produit=arachide,
                annee=year,
                defaults={
                    'rendement_reel_kg_ha': Decimal(str(round(rendement_arachide, 2))),
                    'pluviometrie_mm': Decimal(str(round(pluvio_diourbel, 2)))
                }
            )

            # Richard Toll - Riz (Sol Deck, irrigation)
            HistoriqueRendement.objects.update_or_create(
                localite=richard_toll,
                produit=riz,
                annee=year,
                defaults={
                    'rendement_reel_kg_ha': Decimal(str(round(random.uniform(4000, 5500), 2))),
                    'pluviometrie_mm': Decimal(str(round(random.uniform(200, 400), 2)))
                }
            )

        self.stdout.write(self.style.SUCCESS("✅ Données Mock ML générées avec succès !"))
