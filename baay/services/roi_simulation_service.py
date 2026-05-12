"""
Service de simulation ROI pour Andd Baay V2.
Gère les scénarios prévisionnels et la comparaison avec les données réelles.
"""

import logging
from typing import Optional
from decimal import Decimal
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Sum

from baay.models import Projet, ProjetProduit, SimulationROI, Investissement, Recette

logger = logging.getLogger(__name__)


@dataclass
class ScenarioHypotheses:
    """Hypothèses pour un scénario de simulation."""
    rendement_kg_ha: Decimal
    prix_fcfa_kg: Decimal
    investissement_total: Decimal
    description: str = ""


@dataclass
class SimulationResult:
    """Résultat d'une simulation ROI."""
    recette_prevue: Decimal
    benefice_prevu: Decimal
    roi_pct: Decimal
    rentabilite: str  # 'positive', 'negative', 'equilibre'


# Références de rendement par culture (kg/ha) - valeurs indicatives pour Sahel
RENDEMENTS_REFERENCE = {
    'mil': (800, 1200, 1800),      # (min, moyen, max)
    'sorgho': (1000, 1500, 2500),
    'mais': (1500, 3000, 5000),
    'arachide': (600, 1000, 1500),
    'niebe': (400, 800, 1200),
    'riz': (2000, 4000, 6000),
    'coton': (1500, 2500, 3500),
    'tomate': (10000, 20000, 30000),
    'oignon': (12000, 20000, 28000),
    'piment': (8000, 15000, 25000),
}

# Prix de référence (FCFA/kg) - moyennes indicatives
PRIX_REFERENCE = {
    'mil': (150, 200, 300),
    'sorgho': (120, 180, 250),
    'mais': (100, 150, 250),
    'arachide': (300, 400, 600),
    'niebe': (250, 350, 500),
    'riz': (250, 350, 500),
    'coton': (250, 300, 400),
    'tomate': (150, 250, 400),
    'oignon': (100, 200, 350),
    'piment': (200, 400, 600),
}


def _detect_culture(produit_nom: str) -> str:
    """Détecte la culture à partir du nom du produit."""
    nom_lower = produit_nom.lower()
    for culture in RENDEMENTS_REFERENCE.keys():
        if culture in nom_lower:
            return culture
    return 'mil'  # default


def generer_scenarios_par_defaut(projet: Projet, projet_produit: Optional[ProjetProduit] = None) -> dict[str, ScenarioHypotheses]:
    """
    Génère les 3 scénarios par défaut (optimiste, réaliste, pessimiste)
    basés sur la culture et les données existantes.
    """
    culture_key = _detect_culture(projet_produit.produit.nom if projet_produit else projet.culture.nom if projet.culture else "mil")
    
    # Récupérer investissements réels
    investissements = Investissement.objects.filter(projet=projet).aggregate(
        total=Sum('cout_par_hectare')
    )['total'] or Decimal('0')
    
    # Superficie
    superficie = projet_produit.superficie_allouee if projet_produit else projet.superficie
    
    # Get reference values
    rend_min, rend_moy, rend_max = RENDEMENTS_REFERENCE.get(culture_key, (800, 1200, 1800))
    prix_min, prix_moy, prix_max = PRIX_REFERENCE.get(culture_key, (150, 200, 300))
    
    # Ajustement prix selon saison (à implémenter avec données météo)
    # Pour l'instant, valeurs de base
    
    scenarios = {
        'pessimiste': ScenarioHypotheses(
            rendement_kg_ha=Decimal(str(rend_min)),
            prix_fcfa_kg=Decimal(str(prix_min)),
            investissement_total=investissements * Decimal('1.2'),  # +20% imprévus
            description=f"Scénario prudent: rendement bas ({rend_min} kg/ha), prix bas marché"
        ),
        'realiste': ScenarioHypotheses(
            rendement_kg_ha=Decimal(str(rend_moy)),
            prix_fcfa_kg=Decimal(str(prix_moy)),
            investissement_total=investissements,
            description=f"Scénario réaliste: rendement moyen ({rend_moy} kg/ha), prix moyen marché"
        ),
        'optimiste': ScenarioHypotheses(
            rendement_kg_ha=Decimal(str(rend_max)),
            prix_fcfa_kg=Decimal(str(prix_max)),
            investissement_total=investissements * Decimal('0.9'),  # -10% efficacité
            description=f"Scénario optimiste: bon rendement ({rend_max} kg/ha), prix haut marché"
        ),
    }
    
    return scenarios


def calculer_simulation(
    hypotheses: ScenarioHypotheses,
    superficie: Decimal
) -> SimulationResult:
    """Calcule les résultats d'une simulation à partir des hypothèses."""
    
    # Recette prévue
    recette = hypotheses.rendement_kg_ha * hypotheses.prix_fcfa_kg * superficie
    
    # Bénéfice
    benefice = recette - hypotheses.investissement_total
    
    # ROI
    if hypotheses.investissement_total > 0:
        roi = (benefice / hypotheses.investissement_total) * 100
    else:
        roi = Decimal('0')
    
    # Rentabilité
    if benefice > 0:
        rentabilite = 'positive'
    elif benefice < 0:
        rentabilite = 'negative'
    else:
        rentabilite = 'equilibre'
    
    return SimulationResult(
        recette_prevue=recette,
        benefice_prevu=benefice,
        roi_pct=roi,
        rentabilite=rentabilite,
    )


def creer_simulation(
    projet: Projet,
    cree_par,
    scenario_type: str = 'realiste',
    projet_produit: Optional[ProjetProduit] = None,
    nom_simulation: str = "",
    rendement_kg_ha: Optional[Decimal] = None,
    prix_fcfa_kg: Optional[Decimal] = None,
    investissement_total: Optional[Decimal] = None,
    description: str = "",
) -> SimulationROI:
    """
    Crée une simulation ROI avec calculs automatiques.
    Si valeurs non fournies, utilise les scénarios par défaut.
    """
    # Générer scénarios par défaut si besoin
    if rendement_kg_ha is None or prix_fcfa_kg is None or investissement_total is None:
        scenarios = generer_scenarios_par_defaut(projet, projet_produit)
        scenario_default = scenarios.get(scenario_type, scenarios['realiste'])
        
        rendement_kg_ha = rendement_kg_ha or scenario_default.rendement_kg_ha
        prix_fcfa_kg = prix_fcfa_kg or scenario_default.prix_fcfa_kg
        investissement_total = investissement_total or scenario_default.investissement_total
        
        if not description:
            description = scenario_default.description
    
    # Créer la simulation
    with transaction.atomic():
        simulation = SimulationROI.objects.create(
            projet=projet,
            projet_produit=projet_produit,
            scenario_type=scenario_type,
            nom_simulation=nom_simulation,
            rendement_prevu_kg_ha=rendement_kg_ha,
            prix_prevu_fcfa_kg=prix_fcfa_kg,
            investissement_prevu=investissement_total,
            description=description,
            cree_par=cree_par,
            # Les champs calculés sont remplis par clean()
        )
    
    logger.info(
        "Simulation ROI créée: projet=%s, type=%s, ROI=%s%%",
        projet.nom,
        scenario_type,
        simulation.roi_calcule_pct
    )
    
    return simulation


def mettre_a_jour_recette_reelle(simulation: SimulationROI) -> None:
    """
    Met à jour la comparaison réel vs prévisionnel pour une simulation.
    Appelé automatiquement quand des recettes sont validées.
    """
    # Calculer recettes réelles validées
    recettes_reelles = Recette.objects.filter(
        projet=simulation.projet,
        projet_produit=simulation.projet_produit,
        statut_validation=Recette.STATUT_VALIDEE,
    ).aggregate(total=Sum('montant_total'))['total'] or Decimal('0')
    
    if recettes_reelles > 0:
        simulation.recette_reelle = recettes_reelles
        simulation.save(update_fields=['recette_reelle', 'ecart_reel_pct'])
        
        logger.info(
            "Simulation ROI mise à jour avec réel: projet=%s, écart=%s%%",
            simulation.projet.nom,
            simulation.ecart_reel_pct
        )


def comparer_scenarios(projet: Projet) -> dict:
    """
    Retourne une comparaison des 3 scénarios pour un projet.
    """
    scenarios = generer_scenarios_par_defaut(projet)
    superficie = projet.superficie or Decimal('1')
    
    resultats = {}
    for nom, hypotheses in scenarios.items():
        resultat = calculer_simulation(hypotheses, superficie)
        resultats[nom] = {
            'rendement_kg_ha': hypotheses.rendement_kg_ha,
            'prix_fcfa_kg': hypotheses.prix_fcfa_kg,
            'investissement': hypotheses.investissement_total,
            'recette_prevue': resultat.recette_prevue,
            'benefice_prevu': resultat.benefice_prevu,
            'roi_pct': resultat.roi_pct,
            'rentabilite': resultat.rentabilite,
            'description': hypotheses.description,
        }
    
    return resultats


def obtenir_dernieres_simulations(projet: Projet, limite: int = 5) -> list[SimulationROI]:
    """Retourne les dernières simulations pour un projet."""
    return SimulationROI.objects.filter(
        projet=projet
    ).select_related('projet_produit').order_by('-date_simulation')[:limite]


def dupliquer_simulation(simulation: SimulationROI, cree_par, modifications: dict = None) -> SimulationROI:
    """
    Duplique une simulation existante avec possibilité de modifications.
    """
    nouvelle = SimulationROI(
        projet=simulation.projet,
        projet_produit=simulation.projet_produit,
        scenario_type='personnalise',
        nom_simulation=f"Copie de {simulation.nom_simulation or simulation.get_scenario_type_display()}",
        rendement_prevu_kg_ha=modifications.get('rendement', simulation.rendement_prevu_kg_ha),
        prix_prevu_fcfa_kg=modifications.get('prix', simulation.prix_prevu_fcfa_kg),
        investissement_prevu=modifications.get('investissement', simulation.investissement_prevu),
        description=f"Duplication de simulation #{str(simulation.id)[:8]}",
        cree_par=cree_par,
    )
    nouvelle.save()
    return nouvelle
