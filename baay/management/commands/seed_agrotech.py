from django.core.management.base import BaseCommand
from baay.models import Localite, ProduitAgricole, HistoriqueRendement, ParametresCulture
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
                'rendement_moyen': 1100
            }
        )
        riz, _ = ProduitAgricole.objects.get_or_create(
            nom="Riz",
            defaults={
                'saison': 'Contre-saison', 
                'prix_par_kg': 350,
                'rendement_moyen': 4500
            }
        )

        # Ajout des ParametresCulture
        ParametresCulture.objects.update_or_create(
            produit=arachide,
            defaults={'besoin_eau_mm': 550, 'cycle_croissance_jours': 110, 'temperature_min': 20, 'temperature_max': 35}
        )
        ParametresCulture.objects.update_or_create(
            produit=riz,
            defaults={'besoin_eau_mm': 900, 'cycle_croissance_jours': 120, 'temperature_min': 22, 'temperature_max': 38}
        )

        self.stdout.write('Création de localités modèles...')
        diourbel, _ = Localite.objects.get_or_create(
            nom="Diourbel",
            defaults={'type_sol': 'Dior'}
        )
        richard_toll, _ = Localite.objects.get_or_create(
            nom="Richard Toll",
            defaults={'type_sol': 'Deck'}
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
