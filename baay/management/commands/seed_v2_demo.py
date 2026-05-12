#!/usr/bin/env python
"""
Commande de génération de données fictives pour démonstration Andd Baay V2.
Usage: python manage.py seed_v2_demo [--clean]
"""

import random
from datetime import datetime, timedelta, date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

from baay.models import (
    Profile,
    Ferme,
    Pays,
    Region,
    Localite,
    Projet,
    ProjetProduit,
    ProduitAgricole,
    HistoriqueSol,
    Recette,
    Investissement,
    Tache,
    SimulationROI,
    OffreProduit,
    TransactionMarche,
    RecommandationFertilisation,
    IncidentRapporte,
)


class Command(BaseCommand):
    help = "Génère des données fictives pour démonstration V2"

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Supprime les données existantes avant de créer',
        )
        parser.add_argument(
            '--user',
            type=str,
            default='demo',
            help='Nom d\'utilisateur pour associer les données',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('🌾 Andd Baay V2 - Génération données démo'))

        if options['clean']:
            self.clean_data()

        # Créer ou récupérer utilisateur
        user, profile = self.get_or_create_user(options['user'])

        # Géographie
        pays, regions = self.create_geographie()

        # Ferme
        ferme = self.create_ferme(user, profile, pays, regions)

        # Analyses sol
        sols = self.create_historiques_sol(ferme)

        # Projets avec données complètes
        projets = self.create_projets_v2(ferme, profile, regions)

        # Finance - Recettes et workflow validation
        self.create_finance_workflow(projets, profile)

        # Simulations ROI
        self.create_simulations_roi(projets, profile)

        # Dashboard Bento - Tâches
        self.create_taches_bento(projets, profile)

        # Recommandations IA
        self.create_recommandations_ia(projets, sols, profile)

        # Incidents
        self.create_incidents(projets, profile)

        # Marketplace
        self.create_marketplace(ferme, profile, regions)

        # Stats
        self.stdout.write(self.style.SUCCESS('\n✅ Données de démonstration créées avec succès !'))
        self.stdout.write(self.style.NOTICE('\n📊 Résumé:'))
        self.stdout.write(f"  • Ferme: {ferme.nom}")
        self.stdout.write(f"  • Projets: {len(projets)}")
        self.stdout.write(f"  • Login: {user.username} / password: demo123")
        self.stdout.write(f"\n🔗 URLs à tester:")
        self.stdout.write(f"  • Dashboard: http://localhost:8000/dashboard/")
        self.stdout.write(f"  • Finance: http://localhost:8000/finance/validation/")
        self.stdout.write(f"  • Carte: http://localhost:8000/carte/heatmap/")
        self.stdout.write(f"  • Marketplace: http://localhost:8000/marketplace/")

    def clean_data(self):
        """Nettoie les données V2 existantes."""
        self.stdout.write(self.style.WARNING('🗑️  Nettoyage des données existantes...'))
        models_to_clean = [
            TransactionMarche, OffreProduit, SimulationROI,
            IncidentRapporte, RecommandationFertilisation,
            Recette, Investissement, Tache, ProjetProduit,
        ]
        for model in models_to_clean:
            count = model.objects.all().count()
            model.objects.all().delete()
            if count > 0:
                self.stdout.write(f"  - {model.__name__}: {count} supprimés")

    def get_or_create_user(self, username):
        """Crée ou récupère utilisateur démo."""
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@anddbaay.demo',
                'first_name': 'Demo',
                'last_name': 'User',
            }
        )
        if created:
            user.set_password('demo123')
            user.save()
            self.stdout.write(f"👤 Utilisateur créé: {username} / demo123")
        else:
            user.set_password('demo123')
            user.save()
            self.stdout.write(f"👤 Utilisateur existant mis à jour: {username}")

        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={'nom': f'{username}@anddbaay.demo'}
        )
        return user, profile

    def create_geographie(self):
        """Crée la géographie de démo (Sénégal)."""
        pays, _ = Pays.objects.get_or_create(
            nom="Sénégal",
            defaults={'code_iso': 'SN'}
        )

        regions_data = [
            "Dakar", "Thiès", "Saint-Louis", "Kaolack",
            "Ziguinchor", "Tambacounda", "Kolda",
        ]

        regions = []
        for nom in regions_data:
            region, _ = Region.objects.get_or_create(
                nom=f"Région {nom}",
                pays=pays,
            )
            regions.append(region)

        return pays, regions

    def create_ferme(self, user, profile, pays, regions):
        """Crée une ferme de démo."""
        ferme, _ = Ferme.objects.get_or_create(
            nom="Ferme Demo Baay",
            defaults={
                'proprietaire': profile,
                'pays': pays,
                'region': regions[1] if regions else None,
                'superficie_totale': Decimal('25.00'),
            }
        )
        self.stdout.write(f"🏡 Ferme: {ferme.nom}")
        return ferme

    def create_historiques_sol(self, ferme):
        """Crée des analyses de sol variées."""
        sols = []
        sols_data = [
            {'parcelle_nom': 'Parcelle Nord', 'ph': 5.2, 'n': 35, 'p': 12, 'k': 150, 'mo': 1.2},
            {'parcelle_nom': 'Parcelle Sud', 'ph': 6.8, 'n': 80, 'p': 25, 'k': 200, 'mo': 2.5},
            {'parcelle_nom': 'Parcelle Est', 'ph': 5.8, 'n': 45, 'p': 18, 'k': 120, 'mo': 1.8},
        ]

        for data in sols_data:
            sol, _ = HistoriqueSol.objects.get_or_create(
                ferme=ferme,
                parcelle_nom=data['parcelle_nom'],
                defaults={
                    'ph': data['ph'],
                    'azote_ppm': data['n'],
                    'phosphore_ppm': data['p'],
                    'potassium_ppm': data['k'],
                    'date_mesure': date.today() - timedelta(days=30),
                }
            )
            sols.append(sol)

        self.stdout.write(f"🌱 Analyses sol créées: {len(sols)} parcelles")
        return sols

    def create_projets_v2(self, ferme, profile, regions):
        """Crée des projets avec données complètes pour V2."""
        projets = []
        cultures_data = [
            ('Mil', 90, 'cereale'),
            ('Maïs', 120, 'cereale'),
            ('Arachide', 105, 'legumineuse'),
            ('Niébé', 75, 'legumineuse'),
        ]

        for i, (culture_nom, cycle, type_culture) in enumerate(cultures_data):
            produit, _ = ProduitAgricole.objects.get_or_create(
                nom=culture_nom,
                defaults={
                    "cycle_culture_jours": cycle,
                    "description": f"Culture {type_culture} (démo seed V2).",
                },
            )

            # Coordonnées fictives pour le Sénégal
            coords = [
                (14.7167, -17.4677),  # Dakar
                (14.7894, -16.9286),  # Thiès
                (16.0179, -16.4896),  # Saint-Louis
                (14.1652, -16.0754),  # Kaolack
            ]
            lat, lon = coords[i % len(coords)]

            localite = Localite.objects.filter(region=regions[i % len(regions)]).first()
            if not localite:
                localite = Localite.objects.create(
                    nom=f"Localite {culture_nom}",
                    region=regions[i % len(regions)],
                    latitude=lat,
                    longitude=lon,
                )

            ha = Decimal(str(round(random.uniform(2, 8), 2)))
            pays_projet = ferme.pays
            if not pays_projet and localite.region_id:
                pays_projet = localite.region.pays

            projet = Projet.objects.create(
                nom=f"Projet {culture_nom} {date.today().year}",
                ferme=ferme,
                localite=localite,
                statut=random.choice(["en_cours", "en_cours", "en_pause"]),
                budget_alloue=Decimal(random.randint(500000, 2000000)),
                date_lancement=date.today() - timedelta(days=random.randint(10, 60)),
                date_fin=date.today() + timedelta(days=cycle - random.randint(10, 40)),
                utilisateur=profile,
                pays=pays_projet,
                culture=produit,
                superficie=ha,
            )

            # Ligne culture (superficie_allouee ≤ superficie projet)
            ProjetProduit.objects.create(
                projet=projet,
                produit=produit,
                superficie_allouee=ha,
                date_semis=projet.date_lancement + timedelta(days=1),
            )

            projets.append(projet)

        self.stdout.write(f"📁 Projets créés: {len(projets)}")
        return projets

    def create_finance_workflow(self, projets, profile):
        """Crée recettes avec workflow validation."""
        count = 0
        for projet in projets:
            pp = projet.projet_produits.first()
            libelle_prod = pp.produit.nom if pp else "Récolte"

            # Recettes en attente / validées
            for i in range(random.randint(1, 3)):
                qte = Decimal(random.randint(100, 800))
                pu = Decimal(random.randint(150, 450))
                Recette.objects.create(
                    projet=projet,
                    projet_produit=pp,
                    produit=libelle_prod,
                    quantite=qte,
                    unite=Recette.UNITE_KG,
                    prix_unitaire=pu,
                    date_vente=date.today() - timedelta(days=random.randint(1, 15)),
                    statut_validation=random.choice(
                        [Recette.STATUT_EN_ATTENTE, Recette.STATUT_EN_ATTENTE, Recette.STATUT_VALIDEE]
                    ),
                )
                count += 1

            # Investissements (coût / ha + autres frais)
            for i in range(random.randint(2, 4)):
                Investissement.objects.create(
                    projet=projet,
                    projet_produit=pp,
                    libelle=f"Dépense {i + 1}",
                    categorie=random.choice(
                        ["intrant", "main_oeuvre", "transport", "irrigation", "materiel"]
                    ),
                    cout_par_hectare=Decimal(random.randint(5000, 45000)),
                    autres_frais=Decimal(random.randint(0, 80000)),
                    date_investissement=projet.date_lancement + timedelta(days=random.randint(1, 30)),
                    description=f"Charge démo {i + 1} — {projet.nom}",
                )

        self.stdout.write(f"💰 Finance: {count} recettes créées")

    def create_simulations_roi(self, projets, profile):
        """Crée simulations ROI pour démo."""
        count = 0
        for projet in projets[:2]:  # 2 projets avec simulations
            pp = projet.projet_produits.first()
            for scenario in ["optimiste", "realiste", "pessimiste"]:
                facteurs = {
                    "optimiste": (Decimal("1400"), Decimal("320"), Decimal("650000")),
                    "realiste": (Decimal("1100"), Decimal("280"), Decimal("520000")),
                    "pessimiste": (Decimal("850"), Decimal("240"), Decimal("420000")),
                }
                rendement_kg_ha, prix_fcfa_kg, investissement = facteurs[scenario]

                SimulationROI.objects.create(
                    projet=projet,
                    projet_produit=pp,
                    scenario_type=scenario,
                    nom_simulation=scenario.capitalize(),
                    description=f"Scénario {scenario} pour {projet.nom}",
                    rendement_prevu_kg_ha=rendement_kg_ha,
                    prix_prevu_fcfa_kg=prix_fcfa_kg,
                    investissement_prevu=investissement,
                    cree_par=profile,
                )
                count += 1

        self.stdout.write(f"📈 Simulations ROI: {count} créées")

    def create_taches_bento(self, projets, profile):
        """Crée tâches pour dashboard Bento."""
        taches_data = [
            ("Fertilisation NPK", "fertilisation", "haute"),
            ("Désherbage manuel", "desherbage", "normale"),
            ("Contrôle ravageurs", "phyto", "haute"),
            ("Irrigation complémentaire", "irrigation", "normale"),
            ("Récolte prévisionnelle", "recolte", "normale"),
        ]

        count = 0
        for projet in projets:
            ferme = projet.ferme
            for titre, type_tache, priorite in random.sample(taches_data, 3):
                Tache.objects.create(
                    ferme=ferme,
                    projet=projet,
                    titre=f"{titre} - {projet.nom[:15]}",
                    description=f"Tâche de {type_tache} à effectuer",
                    assigne_a=profile,
                    assigne_par=profile,
                    priorite=priorite,
                    statut=random.choice(["a_faire", "en_cours", "a_faire"]),
                    date_echeance=date.today() + timedelta(days=random.randint(1, 14)),
                )
                count += 1

        self.stdout.write(f"✅ Tâches créées: {count}")

    def create_recommandations_ia(self, projets, sols, profile):
        """Crée recommandations fertilisation."""
        engrais = [
            ("NPK 15-15-15", "mineral_npk", Decimal("150")),
            ("Urée 46%", "mineral_uree", Decimal("50")),
            ("Fumier composté", "organique", Decimal("2000")),
            ("Chaux agricole", "mixte", Decimal("500")),
        ]

        count = 0
        for i, projet in enumerate(projets):
            pp = projet.projet_produits.first()
            if pp:
                sol = sols[i % len(sols)]
                engrais_nom, type_eng, qte = random.choice(engrais)

                RecommandationFertilisation.objects.create(
                    historique_sol=sol,
                    culture_cible=pp.produit,
                    type_engrais_conseille=type_eng,
                    quantite_kg_ha=qte,
                    message_explication=(
                        f"Recommandation démo : {engrais_nom} — sol N={sol.azote_ppm} ppm, "
                        f"pH={sol.ph}. Stade indicatif {random.randint(20, 60)} j."
                    ),
                    priorite_actions=[
                        {"action": f"Prévoir apport {engrais_nom}", "urgence": "moyenne"},
                    ],
                    confiance_score=Decimal("0.82"),
                )
                count += 1

        self.stdout.write(f"🤖 Recommandations IA: {count} créées")

    def create_incidents(self, projets, profile):
        """Crée incidents rapportés."""
        incidents_data = [
            ("Attaque chenilles", "invasion_ravageurs", "moyenne", "Vue sur 3 plants"),
            ("Feuilles jaunissent", "maladie_feuilles", "moyenne", "Début symptôme"),
            ("Vent fort hier", "autre", "faible", "Pas de dégât visible"),
            ("Manque eau", "stress_hydrique", "haute", "3 jours sans pluie"),
        ]

        count = 0
        for projet in projets[:3]:
            loc = projet.localite
            lat = float(loc.latitude) if loc and loc.latitude is not None else None
            lon = float(loc.longitude) if loc and loc.longitude is not None else None
            for _titre, type_inc, gravite, desc in random.sample(incidents_data, 2):
                IncidentRapporte.objects.create(
                    ferme=projet.ferme,
                    signale_par=profile,
                    type_incident=type_inc,
                    gravite_detectee=gravite,
                    transcription_audio=desc,
                    localisation_gps_lat=lat,
                    localisation_gps_lon=lon,
                )
                count += 1

        self.stdout.write(f"⚠️  Incidents créés: {count}")

    def create_marketplace(self, ferme, profile, regions):
        """Crée offres marketplace."""
        produits_market = ['Mil blanc', 'Maïs jaune', 'Arachide coque', 'Niébé rouge']
        unites = ['kg', 'sac', 'tonne']
        qualites = ['A', 'B', 'A']

        # Créer quelques offres
        count_offres = 0
        for i, prod_nom in enumerate(produits_market):
            produit, _ = ProduitAgricole.objects.get_or_create(
                nom=prod_nom,
                defaults={"description": "Produit marketplace (démo seed V2)."},
            )

            localite = Localite.objects.filter(region__in=regions).order_by('?').first()

            offre = OffreProduit.objects.create(
                vendeur=ferme,
                produit=produit,
                titre_annonce=f"{prod_nom} de qualité {qualites[i % len(qualites)]} - Récolte 2026",
                description=f"Stock disponible de {prod_nom}. Produit localement à {localite.nom if localite else 'Thiès'}.",
                quantite_disponible=Decimal(random.randint(50, 500)),
                unite=unites[i % len(unites)],
                prix_unitaire=Decimal(random.randint(200, 600)),
                prix_negociable=True,
                qualite=qualites[i % len(qualites)],
                localite_retrait=localite,
                livraison_possible=random.choice([True, False]),
                date_expiration=date.today() + timedelta(days=30),
                cree_par=profile,
            )
            count_offres += 1

        self.stdout.write(f"🏪 Offres marketplace: {count_offres} créées")
