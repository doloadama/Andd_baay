"""
Commande : seed_projets_fictifs
================================
Génère 60 projets agricoles clôturés fictifs mais agronomiquement réalistes
pour tester et calibrer le moteur de prédiction (MAPE, biais, PrevisionFeatures).

Scénarios couverts
------------------
  - 8 cultures principales : Mil, Arachide, Niébé, Sorgho, Riz, Maïs, Tomate, Oignon
  - 6 localités au Sénégal avec sol et pluviométrie authentiques
  - Irrigué vs pluvial, engrais organique/minéral/mixte/aucun
  - Associations légumineuse + céréale (niébé + mil)
  - Observations terrain (etat_vegetatif 1–5)
  - Campagnes 2020–2024 (5 ans)
  - Bruit réaliste sur le rendement final (±15–30 %)

Usage
-----
    python manage.py seed_projets_fictifs
    python manage.py seed_projets_fictifs --reset   # efface d'abord les données fictives
    python manage.py seed_projets_fictifs --n 80    # nombre de projets
"""

import random
import math
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

SEED = 42
random.seed(SEED)


# ── Données agronomiques de référence ──────────────────────────────────────
# Rendement moyen réel kg/ha (sources FAO/ISRA Sénégal)
_REND_MOYEN = {
    # sols valides : Dior, Deck, Deck-Dior, Sablonneux, Latéritique
    "Mil":     {"base": 900,  "max": 1400, "sol_ok": ["Dior", "Deck-Dior"],  "sol_nok": ["Latéritique"],           "pluie": 350, "cycle": 90,  "saison": "Hivernage"},
    "Arachide":{"base": 1000, "max": 1600, "sol_ok": ["Dior", "Deck-Dior"],  "sol_nok": ["Deck", "Latéritique"],  "pluie": 400, "cycle": 110, "saison": "Hivernage"},
    "Niébé":   {"base": 500,  "max": 900,  "sol_ok": ["Dior", "Sablonneux"], "sol_nok": [],                       "pluie": 300, "cycle": 80,  "saison": "Hivernage"},
    "Sorgho":  {"base": 1100, "max": 1800, "sol_ok": ["Deck", "Deck-Dior"],  "sol_nok": ["Latéritique"],          "pluie": 400, "cycle": 110, "saison": "Hivernage"},
    "Riz":     {"base": 3500, "max": 5500, "sol_ok": ["Deck", "Deck-Dior"],  "sol_nok": ["Dior", "Sablonneux"],   "pluie": 900, "cycle": 120, "saison": "Hivernage"},
    "Maïs":    {"base": 2000, "max": 3500, "sol_ok": ["Deck", "Deck-Dior"],  "sol_nok": ["Sablonneux"],           "pluie": 600, "cycle": 100, "saison": "Hivernage"},
    "Tomate":  {"base": 14000,"max": 25000,"sol_ok": ["Deck", "Deck-Dior"],  "sol_nok": ["Latéritique"],          "pluie": 600, "cycle": 90,  "saison": "Contre-saison"},
    "Oignon":  {"base": 18000,"max": 28000,"sol_ok": ["Sablonneux", "Deck"], "sol_nok": ["Latéritique"],          "pluie": 500, "cycle": 100, "saison": "Contre-saison"},
}

# Localités sénégalaises — sols restreints aux choix valides (Dior/Deck/Deck-Dior/Sablonneux/Latéritique)
_LOCALITES = [
    # (nom, type_sol, pluie_mm, lat, lon, zone)
    ("Thiès",         "Dior",       500,  14.833, -16.933, "sahel"),
    ("Kaolack",       "Deck-Dior",  620,  14.133, -16.250, "sahel"),
    ("Ziguinchor",    "Deck",       1350, 12.583, -16.267, "casamance"),
    ("Tambacounda",   "Deck-Dior",  820,  13.767, -13.667, "sine-saloum"),
    ("Saint-Louis",   "Sablonneux", 280,  16.033, -16.483, "nord"),
    ("Kolda",         "Deck",       1100, 12.883, -14.950, "casamance"),
]

# Profils de projets fictifs
_PROFILS = [
    # (cultures, irrigat, engrais, superficie_ha, etat_veg_range, localite_zone)
    # Hivernage sahel — Mil pluvial traditionnel
    {"cultures": ["Mil"],                       "irrig": "Aucune",          "engrais": "Aucun",        "ha": (1.0, 3.0), "eveg": (2, 4), "zone": "sahel"},
    {"cultures": ["Mil"],                       "irrig": "Aucune",          "engrais": "Organique",    "ha": (2.0, 5.0), "eveg": (3, 5), "zone": "sahel"},
    {"cultures": ["Mil"],                       "irrig": "Aucune",          "engrais": "Minéral NPK",  "ha": (2.0, 6.0), "eveg": (3, 5), "zone": "sahel"},
    # Association Mil + Niébé
    {"cultures": ["Mil", "Niébé"],              "irrig": "Aucune",          "engrais": "Aucun",        "ha": (2.0, 4.0), "eveg": (3, 5), "zone": "sahel"},
    {"cultures": ["Mil", "Niébé"],              "irrig": "Aucune",          "engrais": "Organique",    "ha": (3.0, 6.0), "eveg": (3, 5), "zone": "sahel"},
    # Arachide
    {"cultures": ["Arachide"],                  "irrig": "Aucune",          "engrais": "Aucun",        "ha": (1.0, 4.0), "eveg": (2, 4), "zone": "sahel"},
    {"cultures": ["Arachide"],                  "irrig": "Aucune",          "engrais": "Minéral NPK",  "ha": (2.0, 5.0), "eveg": (3, 5), "zone": "sahel"},
    # Niébé seul
    {"cultures": ["Niébé"],                     "irrig": "Aucune",          "engrais": "Aucun",        "ha": (0.5, 2.0), "eveg": (2, 4), "zone": "sahel"},
    # Sorgho
    {"cultures": ["Sorgho"],                    "irrig": "Aucune",          "engrais": "Organique",    "ha": (1.5, 4.0), "eveg": (2, 4), "zone": "sine-saloum"},
    {"cultures": ["Sorgho"],                    "irrig": "Aucune",          "engrais": "Minéral NPK",  "ha": (2.0, 5.0), "eveg": (3, 5), "zone": "sine-saloum"},
    # Riz irrigué (Casamance)
    {"cultures": ["Riz"],                       "irrig": "Gravitaire",      "engrais": "Mixte",        "ha": (1.0, 3.0), "eveg": (3, 5), "zone": "casamance"},
    {"cultures": ["Riz"],                       "irrig": "Aspersion",       "engrais": "Minéral NPK",  "ha": (2.0, 5.0), "eveg": (3, 5), "zone": "casamance"},
    # Maïs
    {"cultures": ["Maïs"],                      "irrig": "Aspersion",       "engrais": "Mixte",        "ha": (1.0, 3.0), "eveg": (3, 5), "zone": "casamance"},
    {"cultures": ["Maïs"],                      "irrig": "Aucune",          "engrais": "Minéral NPK",  "ha": (2.0, 5.0), "eveg": (2, 4), "zone": "casamance"},
    # Maraîchage irrigué
    {"cultures": ["Tomate"],                    "irrig": "Goutte-à-goutte", "engrais": "Mixte",        "ha": (0.25, 1.5), "eveg": (4, 5), "zone": "casamance"},
    {"cultures": ["Oignon"],                    "irrig": "Goutte-à-goutte", "engrais": "Mixte",        "ha": (0.25, 1.0), "eveg": (3, 5), "zone": "nord"},
    {"cultures": ["Tomate"],                    "irrig": "Aspersion",       "engrais": "Organique",    "ha": (0.5, 2.0), "eveg": (3, 4), "zone": "casamance"},
    # Projet mixte (Arachide + Niébé)
    {"cultures": ["Arachide", "Niébé"],         "irrig": "Aucune",          "engrais": "Aucun",        "ha": (2.0, 4.0), "eveg": (2, 4), "zone": "sahel"},
    # Sol inadapté (stress test)
    {"cultures": ["Riz"],                       "irrig": "Aucune",          "engrais": "Aucun",        "ha": (1.0, 2.0), "eveg": (1, 3), "zone": "nord"},
    {"cultures": ["Sorgho"],                    "irrig": "Aucune",          "engrais": "Aucun",        "ha": (1.5, 3.0), "eveg": (1, 3), "zone": "nord"},
]


def _rendement_final_realiste(culture, sol_type, irrig, engrais, superficie_ha, etat_veg, annee, pluie_mm):
    """
    Calcule un rendement final réaliste (kg total) avec bruit aléatoire.
    Simule les vraies variations de terrain observées au Sénégal.
    """
    ref = _REND_MOYEN.get(culture)
    if not ref:
        return superficie_ha * 800 * random.uniform(0.7, 1.3)

    # Rendement de base kg/ha
    rend_ha = random.uniform(ref["base"] * 0.75, ref["max"] * 0.90)

    # Impact sol
    if sol_type in (ref.get("sol_nok") or []):
        rend_ha *= random.uniform(0.50, 0.72)   # sol inadapté : forte pénalité
    elif sol_type in (ref.get("sol_ok") or []):
        rend_ha *= random.uniform(0.90, 1.10)   # sol adapté : légère prime

    # Impact pluviométrie vs besoin
    besoin = ref["pluie"]
    if pluie_mm < besoin * 0.6 and irrig == "Aucune":
        rend_ha *= random.uniform(0.35, 0.60)   # déficit hydrique sévère
    elif pluie_mm < besoin * 0.85 and irrig == "Aucune":
        rend_ha *= random.uniform(0.65, 0.85)   # déficit modéré
    elif irrig in ("Goutte-à-goutte", "Aspersion", "Gravitaire"):
        rend_ha *= random.uniform(1.10, 1.35)   # irrigation → prime

    # Impact engrais
    if engrais == "Mixte":
        rend_ha *= random.uniform(1.12, 1.25)
    elif "Minéral" in engrais:
        rend_ha *= random.uniform(1.08, 1.18)
    elif engrais == "Organique":
        rend_ha *= random.uniform(1.04, 1.12)

    # Impact état végétatif (observation terrain)
    mult_obs = {1: 0.45, 2: 0.70, 3: 0.95, 4: 1.15, 5: 1.32}
    rend_ha *= mult_obs.get(etat_veg, 1.0)

    # Variabilité inter-annuelle (ENSO : sécheresses 2021-2023 au Sahel)
    if annee == 2021:
        rend_ha *= random.uniform(0.80, 1.05)   # année sèche Sahel
    elif annee == 2022:
        rend_ha *= random.uniform(0.70, 0.92)   # pire La Niña
    elif annee == 2023:
        rend_ha *= random.uniform(0.85, 1.10)
    elif annee == 2024:
        rend_ha *= random.uniform(0.90, 1.15)

    # Bruit aléatoire résiduel (ravageurs, maladies, accidents...)
    rend_ha *= random.uniform(0.85, 1.15)

    total_kg = max(50.0, rend_ha * superficie_ha)
    return round(total_kg, 1)


class Command(BaseCommand):
    help = "Génère des projets agricoles fictifs clôturés pour tester la calibration du modèle IA."

    def add_arguments(self, parser):
        parser.add_argument("--n", type=int, default=60, help="Nombre de projets à créer (defaut: 60).")
        parser.add_argument("--reset", action="store_true", help="Supprimer d'abord les projets fictifs existants.")
        parser.add_argument("--ferme", default=None, help="Nom de la ferme à utiliser (crée 'Ferme Test ML' si absent).")

    def handle(self, *args, **options):
        from baay.models import (
            Ferme, Localite, Projet, ProjetProduit, ProduitAgricole,
            HistoriqueRendement, PrevisionRecolte,
        )
        from baay.services import update_prediction_for_projet_produit

        n_cible = options["n"]

        # ── 0. Reset si demandé ──────────────────────────────────────────────
        if options["reset"]:
            deleted, _ = Projet.objects.filter(nom__startswith="[TEST]").delete()
            self.stdout.write(self.style.WARNING(f"Projets fictifs supprimés : {deleted}"))

        # ── 1. Utilisateur et ferme de test ─────────────────────────────────
        with transaction.atomic():
            user, _ = User.objects.get_or_create(
                username="test_ml_agriculteur",
                defaults={"first_name": "Mamadou", "last_name": "Diallo",
                          "email": "mamadou.diallo.test@baay.sn", "is_active": True},
            )
            if not user.has_usable_password():
                user.set_password("TestML2024!")
                user.save()

            # Créer un profil si absent
            from baay.models import Profile
            Profile.objects.get_or_create(user=user)

            nom_ferme = options["ferme"] or "Ferme Test ML Calibration"
            ferme, _ = Ferme.objects.get_or_create(
                nom=nom_ferme,
                defaults={"proprietaire": user.profile,
                          "description": "Ferme fictive pour calibration du modèle IA."},
            )

        self.stdout.write(f"Ferme : {ferme.nom} (id={ferme.id})")

        # ── 2. Localités enrichies ───────────────────────────────────────────
        # On met à jour les données sol/pluviométrie si elles sont génériques
        localites_map = {}   # zone → list[Localite]
        with transaction.atomic():
            for (nom, sol, pluie, lat, lon, zone) in _LOCALITES:
                loc, _ = Localite.objects.get_or_create(
                    nom=nom,
                    defaults={"type_sol": sol, "pluviometrie_moyenne": pluie,
                              "latitude": lat, "longitude": lon},
                )
                # Mettre à jour si les données agronomiques manquent
                changed = False
                if loc.type_sol in (None, "", "Non spécifié", "Non spécifié"):
                    loc.type_sol = sol; changed = True
                if not loc.pluviometrie_moyenne:
                    loc.pluviometrie_moyenne = pluie; changed = True
                if not loc.latitude:
                    loc.latitude = lat; changed = True
                if not loc.longitude:
                    loc.longitude = lon; changed = True
                if changed:
                    loc.save()
                localites_map.setdefault(zone, []).append(loc)

        self.stdout.write(f"Localités initialisées : {len(_LOCALITES)}")

        # ── 3. Produits disponibles ──────────────────────────────────────────
        produits_map = {}
        for nom_culture in _REND_MOYEN:
            prod = ProduitAgricole.objects.filter(nom__icontains=nom_culture).first()
            if not prod:
                self.stderr.write(self.style.WARNING(f"Produit '{nom_culture}' introuvable en base — ignoré."))
                continue
            produits_map[nom_culture] = prod

        self.stdout.write(f"Produits disponibles : {list(produits_map.keys())}")

        # ── 4. Génération des projets ─────────────────────────────────────────
        annees = list(range(2020, 2025))   # 5 campagnes
        profils_cycle = _PROFILS * math.ceil(n_cible / len(_PROFILS))
        random.shuffle(profils_cycle)
        profils_cycle = profils_cycle[:n_cible]

        created = 0
        skipped = 0

        for idx, profil in enumerate(profils_cycle):
            cultures = profil["cultures"]
            zone = profil["zone"]
            irrig = profil["irrig"]
            engrais = profil["engrais"]
            ha_min, ha_max = profil["ha"]
            eveg_min, eveg_max = profil["eveg"]

            # Filtrer cultures disponibles
            cultures_dispo = [c for c in cultures if c in produits_map]
            if not cultures_dispo:
                skipped += 1
                continue

            # Localité dans la bonne zone
            locs_zone = localites_map.get(zone, [])
            if not locs_zone:
                locs_zone = [loc for locs in localites_map.values() for loc in locs]
            localite = random.choice(locs_zone)

            # Campagne
            annee = random.choice(annees)
            # Date de semis (juin–août pour hivernage, oct–jan pour contre-saison)
            culture_ref = _REND_MOYEN[cultures_dispo[0]]
            if culture_ref["saison"] == "Hivernage":
                date_semis = date(annee, random.randint(6, 8), random.randint(1, 25))
            elif culture_ref["saison"] == "Contre-saison":
                mois_cs = random.choice([10, 11, 12])
                date_semis = date(annee if mois_cs >= 10 else annee + 1, mois_cs, random.randint(1, 20))
            else:
                date_semis = date(annee, random.randint(4, 9), random.randint(1, 20))

            cycle = culture_ref["cycle"]
            date_recolte_effective = date_semis + timedelta(days=cycle + random.randint(-10, 15))
            # S'assurer que le projet est dans le passé
            if date_recolte_effective >= date.today():
                date_recolte_effective = date.today() - timedelta(days=random.randint(30, 180))
                date_semis = date_recolte_effective - timedelta(days=cycle)

            superficie_proj = round(random.uniform(ha_min, ha_max), 2)
            budget = Decimal(str(round(superficie_proj * random.randint(80000, 250000))))
            nom_projet = f"[TEST] {cultures_dispo[0]} {annee} — {localite.nom} #{idx+1:03d}"

            etat_veg = random.randint(eveg_min, eveg_max)

            try:
                with transaction.atomic():
                    # Créer le projet (statut en_cours d'abord)
                    # Créer directement en 'cloture' pour passer la validation
                    # date_fin (qui n'autorise pas le passé pour les projets actifs)
                    projet = Projet(
                        nom=nom_projet,
                        ferme=ferme,
                        localite=localite,
                        statut="cloture",
                        utilisateur=user.profile,
                        superficie=Decimal(str(round(superficie_proj, 2))),
                        type_irrigation=irrig,
                        type_engrais=engrais,
                        budget_alloue=budget,
                        date_lancement=date_semis - timedelta(days=random.randint(5, 15)),
                        date_fin=date_recolte_effective,
                    )
                    projet.save()  # skip full_clean via save() direct

                    # Créer les ProjetProduit
                    pps_crees = []
                    for nom_culture in cultures_dispo:
                        prod = produits_map[nom_culture]
                        # Répartir la superficie entre les cultures
                        part = 1.0 / len(cultures_dispo)
                        superficie_culture = round(superficie_proj * part * random.uniform(0.7, 1.3), 2)
                        superficie_culture = max(0.1, superficie_culture)

                        # date_recolte_prevue doit être <= projet.date_fin
                        date_prev_pp = date_semis + timedelta(days=cycle)
                        if date_prev_pp > date_recolte_effective:
                            date_prev_pp = date_recolte_effective
                        pp = ProjetProduit.objects.create(
                            projet=projet,
                            produit=prod,
                            superficie_allouee=Decimal(str(superficie_culture)),
                            date_semis=date_semis,
                            date_recolte_prevue=date_prev_pp,
                            etat_vegetatif=etat_veg,
                            notes=f"Projet de test (seed) — campagne {annee}. "
                                  f"Zone {zone}, sol {localite.type_sol}, "
                                  f"pluie {localite.pluviometrie_moyenne} mm.",
                        )
                        pps_crees.append((pp, nom_culture))

                    # Calculer les prévisions AVANT de fixer le rendement final
                    # (cela alimente PrevisionFeatures avec les bonnes features)
                    for pp, _ in pps_crees:
                        try:
                            update_prediction_for_projet_produit(pp)
                        except Exception as exc:
                            self.stderr.write(f"  Prevision echouee pour {pp}: {exc}")

                    # Fixer le rendement final avec bruit réaliste
                    for pp, nom_culture in pps_crees:
                        superficie_ha = float(pp.superficie_allouee)
                        rend_final = _rendement_final_realiste(
                            nom_culture,
                            localite.type_sol,
                            irrig,
                            engrais,
                            superficie_ha,
                            etat_veg,
                            annee,
                            float(localite.pluviometrie_moyenne or 300),
                        )
                        pp.rendement_final = Decimal(str(rend_final))
                        pp.date_recolte_effective = date_recolte_effective
                        pp.save(update_fields=["rendement_final", "date_recolte_effective"])
                        # Le signal valider_label_ml_a_cloture est déclenché ici

                    # Le projet est déjà 'cloture' dès la création

                    # Ajouter un HistoriqueRendement (pour le fallback local P1.2)
                    if random.random() < 0.7:   # 70% des projets alimentent l'historique
                        for pp, nom_culture in pps_crees:
                            if pp.rendement_final and pp.superficie_allouee > 0:
                                rend_ha = float(pp.rendement_final) / float(pp.superficie_allouee)
                                HistoriqueRendement.objects.get_or_create(
                                    localite=localite,
                                    produit=produits_map[nom_culture],
                                    annee=annee,
                                    defaults={
                                        "rendement_reel_kg_ha": round(rend_ha, 1),
                                        "pluviometrie_mm": float(localite.pluviometrie_moyenne or 300)
                                            * random.uniform(0.7, 1.3),
                                    },
                                )

                created += 1
                if created % 10 == 0:
                    self.stdout.write(f"  {created}/{n_cible} projets créés...")

            except Exception as exc:
                skipped += 1
                self.stderr.write(self.style.WARNING(f"Projet ignoré ({nom_projet[:50]}): {exc}"))

        # ── 5. Invalider le cache des correcteurs de biais ───────────────────
        try:
            from baay.services.prediction_accuracy import invalider_cache_correcteurs_biais
            invalider_cache_correcteurs_biais()
        except Exception:
            pass

        # ── 5b. Marquer ces données comme SYNTHÉTIQUES ───────────────────────
        # Garde-fou d'intégrité : ces observations sont générées, jamais réelles.
        # Elles ne doivent PAS entrer dans l'entraînement ML (sinon le modèle
        # réapprend le générateur et affiche un R² artificiellement parfait).
        from baay.models import PrevisionFeatures, PrevisionRecolte
        n_marquees = PrevisionFeatures.objects.filter(
            prevision__projet__ferme=ferme,
        ).update(synthetique=True)

        # ── 6. Rapport final ─────────────────────────────────────────────────
        n_previsions = PrevisionRecolte.objects.filter(projet__ferme=ferme).count()
        n_features = PrevisionFeatures.objects.filter(
            prevision__projet__ferme=ferme,
            rendement_reel__isnull=False,
        ).count()
        self.stdout.write(self.style.WARNING(
            f"  {n_marquees} PrevisionFeatures marquées synthetique=True (exclues de l'entraînement ML)."
        ))

        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*55}\n"
            f"  Projets créés          : {created}\n"
            f"  Projets ignorés        : {skipped}\n"
            f"  Prévisions IA générées : {n_previsions}\n"
            f"  PrevisionFeatures ML   : {n_features}\n"
            f"  HistoriqueRendement    : {HistoriqueRendement.objects.count()}\n"
            f"{'='*55}"
        ))
        self.stdout.write(self.style.SUCCESS("\nProchaines étapes :"))
        self.stdout.write("  python manage.py evaluer_previsions")
        self.stdout.write("  python manage.py exporter_dataset_ml --list")
        self.stdout.write("  python manage.py entrainer_modele_ml --all --min-n 5")
