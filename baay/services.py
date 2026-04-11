import random
import logging
from datetime import timedelta
from datetime import date
from .models import HistoriqueRendement

logger = logging.getLogger(__name__)

def estimer_rendement_ia(projet_produit):
    """
    Estime dynamiquement le rendement d'une culture selon des critères agronomiques.
    Prend en compte le type de sol, l'eau, et les dates de semis.
    """
    produit = projet_produit.produit
    projet = projet_produit.projet
    localite = projet.localite

    # Base : Le potentiel max de la culture, ou le rendement moyen, ou un fallback
    rendement_base = produit.rendement_potentiel_max or produit.rendement_moyen or 1000.0
    
    # Superficie
    superficie = float(projet_produit.superficie_allouee or 1.0)
    rendement_total_base = float(rendement_base) * superficie

    penalite = 0.0
    confiance = 80.0 # Confiance de base sans modèle entraîné

    # 1. Vérification du Sol
    sol_inadapte = False
    if localite.type_sol:
        # Exemples de règles simples : L'arachide aime le Dior, le Riz aime le Deck.
        if 'arachide' in produit.nom.lower() and localite.type_sol not in ['Dior', 'Deck-Dior']:
            sol_inadapte = True
        elif 'riz' in produit.nom.lower() and localite.type_sol not in ['Deck', 'Deck-Dior']:
            sol_inadapte = True

    if sol_inadapte:
        penalite += 0.20
        confiance -= 10.0

    # 2. Vérification de l'Eau (Pluviométrie + Irrigation)
    besoin_eau = produit.besoin_eau_mm or 0
    pluie_moyenne = localite.pluviometrie_moyenne or 0
    
    if besoin_eau > 0 and pluie_moyenne < besoin_eau:
        if projet.type_irrigation == 'Aucune':
            penalite += 0.40 # Énorme pénalité de stress hydrique
            confiance -= 20.0
        else:
            # S'il y a de l'irrigation, on compense
            if projet.type_irrigation == 'Goutte-à-goutte':
                confiance += 10.0 # Très efficace
            else:
                confiance += 5.0

    # 3. Évaluation du semis tardif
    if projet_produit.date_semis:
        # En Afrique de l'Ouest, l'hivernage est généralement Juillet-Août.
        # Règle simple: si semis après mi-Août pour une culture d'hivernage
        mois_semis = projet_produit.date_semis.month
        if produit.saison == 'Hivernage' and mois_semis >= 8:
            # Semis tardif
            penalite += 0.15
            confiance -= 10.0

    # 4. Apports (Engrais)
    bonus = 0.0
    if projet.type_engrais != 'Aucun':
        # Bonus variable selon le type d'engrais
        if projet.type_engrais == 'Mixte':
            bonus += 0.15
            confiance += 8.0
        elif 'Minéral' in projet.type_engrais:
            bonus += 0.12
            confiance += 5.0
        elif projet.type_engrais == 'Organique':
            bonus += 0.08
            confiance += 6.0 # L'organique est plus sain sur le long terme

    # Calcul Final
    modificateur = max(0.1, 1.0 - penalite + bonus)
    rendement_cible = rendement_total_base * modificateur
    
    # Fourchette Min/Max (Variance de 10%)
    rendement_min = rendement_cible * 0.90
    rendement_max = rendement_cible * 1.10

    # Calcul Date de récolte prévue
    date_recolte = None
    cycle = produit.cycle_culture_jours or produit.duree_avant_recolte
    if projet_produit.date_semis and cycle:
        date_recolte = projet_produit.date_semis + timedelta(days=cycle)

    return {
        'min': round(rendement_min, 2),
        'max': round(rendement_max, 2),
        'confiance': min(100.0, max(0.0, confiance)),
        'date_recolte_prevue': date_recolte
    }
