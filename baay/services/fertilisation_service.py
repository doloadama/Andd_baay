"""
Service de recommandation de fertilisation basé sur l'analyse N-P-K et pH du sol.
Utilise des règles agronomiques et références FAO pour générer des conseils personnalisés.
"""

import logging
from typing import Optional
from decimal import Decimal
from dataclasses import dataclass

from django.db import transaction

from baay.models import HistoriqueSol, ProduitAgricole, RecommandationFertilisation

logger = logging.getLogger(__name__)


# Références agronomiques pour cultures sahéliennes (valeurs indicatives en ppm)
BESOINS_NPK = {
    # Culture: (N_min, N_optimal, P_min, P_optimal, K_min, K_optimal)
    'arachide': (20, 40, 15, 25, 30, 50),
    'mil': (30, 50, 20, 30, 40, 60),
    'sorgho': (35, 55, 20, 35, 40, 70),
    'mais': (50, 80, 25, 40, 60, 100),
    'riz': (40, 70, 20, 35, 50, 80),
    'niebe': (15, 30, 15, 25, 30, 50),
    'coton': (60, 100, 30, 50, 60, 90),
    'tomate': (50, 90, 30, 50, 70, 120),
    'oignon': (60, 100, 30, 50, 80, 150),
    'piment': (50, 80, 25, 45, 60, 100),
}

# Seuils pH par culture (min, max, optimal)
PH_IDEAL = {
    'arachide': (5.5, 7.0, 6.2),
    'mil': (5.0, 7.5, 6.5),
    'sorgho': (5.5, 8.0, 6.8),
    'mais': (5.5, 7.5, 6.5),
    'riz': (5.0, 6.5, 5.8),
    'niebe': (5.5, 7.0, 6.5),
    'coton': (5.5, 7.5, 6.5),
    'tomate': (6.0, 6.8, 6.4),
    'oignon': (6.0, 7.0, 6.5),
    'piment': (6.0, 7.0, 6.5),
}


@dataclass
class AnalyseNutriments:
    """Résultat d'analyse N-P-K avec écarts aux seuils optimaux."""
    azote_actuel: float
    phosphore_actuel: float
    potassium_actuel: float
    ph_actuel: Optional[float]
    
    deficit_azote: float
    deficit_phosphore: float
    deficit_potassium: float
    ecart_ph: Optional[float]
    
    score_fertilite: float  # 0-1


@dataclass
class ConseilFertilisation:
    """Conseil structuré pour la fertilisation."""
    type_engrais: str
    quantite_kg_ha: Optional[Decimal]
    message: str
    actions_prioritaires: list[dict]
    confiance: float


def _calculer_deficits(historique: HistoriqueSol, culture_key: str) -> AnalyseNutriments:
    """
    Calcule les écarts entre niveaux actuels et besoins de la culture.
    """
    n_act = float(historique.azote_ppm or 0)
    p_act = float(historique.phosphore_ppm or 0)
    k_act = float(historique.potassium_ppm or 0)
    ph_act = float(historique.ph) if historique.ph else None
    
    besoins = BESOINS_NPK.get(culture_key, (30, 50, 20, 30, 40, 70))
    n_min, n_opt, p_min, p_opt, k_min, k_opt = besoins
    
    # Calcul des déficits (positif = manque)
    deficit_n = max(0, n_opt - n_act)
    deficit_p = max(0, p_opt - p_act)
    deficit_k = max(0, k_opt - k_act)
    
    # Écart pH (distance à l'optimal)
    ecart_ph = None
    if ph_act is not None:
        ph_ideal = PH_IDEAL.get(culture_key, (6.0, 6.5))
        ecart_ph = abs(ph_act - ph_ideal[1])
    
    # Score global de fertilité (0-1, 1 = parfait)
    score_n = min(1.0, n_act / n_opt) if n_opt > 0 else 0
    score_p = min(1.0, p_act / p_opt) if p_opt > 0 else 0
    score_k = min(1.0, k_act / k_opt) if k_opt > 0 else 0
    
    # Pénalité pH si hors plage
    penalite_ph = 0
    if ph_act is not None:
        ph_min, ph_max = PH_IDEAL.get(culture_key, (5.5, 7.0))[:2]
        if ph_act < ph_min or ph_act > ph_max:
            penalite_ph = 0.2
    
    score_global = (score_n + score_p + score_k) / 3 - penalite_ph
    score_global = max(0, min(1, score_global))
    
    return AnalyseNutriments(
        azote_actuel=n_act,
        phosphore_actuel=p_act,
        potassium_actuel=k_act,
        ph_actuel=ph_act,
        deficit_azote=deficit_n,
        deficit_phosphore=deficit_p,
        deficit_potassium=deficit_k,
        ecart_ph=ecart_ph,
        score_fertilite=score_global,
    )


def _suggere_type_engrais(analyse: AnalyseNutriments) -> tuple[str, Optional[Decimal]]:
    """
    Suggère le type d'engrais le plus adapté selon les déficits.
    Retourne: (type_engrais, quantite_kg_ha_estimee)
    """
    deficit_n = analyse.deficit_azote
    deficit_p = analyse.deficit_phosphore
    deficit_k = analyse.deficit_potassium
    
    # Logique de décision
    total_deficit = deficit_n + deficit_p + deficit_k
    
    if total_deficit < 10:
        return ('aucun', None)
    
    # Déterminer le nutriment le plus limitant
    max_deficit = max(deficit_n, deficit_p, deficit_k)
    
    # Si un seul nutriment est très déficitaire
    if max_deficit > 50:
        if deficit_n == max_deficit:
            return ('mineral_uree', Decimal(str(max(20, deficit_n / 4))))
        elif deficit_p == max_deficit:
            return ('mineral_npk', Decimal(str(max(30, max_deficit / 3))))
        else:
            return ('mineral_npk', Decimal(str(max(30, max_deficit / 3))))
    
    # Si plusieurs déficits équilibrés
    if deficit_n > 20 and deficit_p > 15 and deficit_k > 25:
        return ('mineral_npk', Decimal('80'))
    
    # Si déficits modérés, privilégier organique pour santé long terme
    if total_deficit < 100:
        return ('organique', Decimal('1500'))  # 1.5 tonnes compost/ha
    
    # Déficits importants: mixte
    if deficit_n > 40 or deficit_p > 30:
        return ('mixte', Decimal('100'))
    
    return ('organique', Decimal('2000'))


def _generer_message(analyse: AnalyseNutriments, type_engrais: str, culture_nom: str) -> str:
    """Génère un message explicatif personnalisé."""
    
    messages = []
    
    # Introduction
    score_pct = round(analyse.score_fertilite * 100)
    messages.append(
        f"Analyse du sol pour {culture_nom}: fertilité globale à {score_pct}%. "
    )
    
    # Détails déficits
    if analyse.deficit_azote > 20:
        messages.append(
            f"⚠️ Déficit azote important ({analyse.deficit_azote:.0f} ppm sous l'optimal). "
            "L'azote est essentiel pour la croissance végétative."
        )
    
    if analyse.deficit_phosphore > 15:
        messages.append(
            f"⚠️ Déficit phosphore ({analyse.deficit_phosphore:.0f} ppm). "
            "Le phosphore favorise le développement racinaire et la floraison."
        )
    
    if analyse.deficit_potassium > 25:
        messages.append(
            f"⚠️ Déficit potassium ({analyse.deficit_potassium:.0f} ppm). "
            "Le potassium renforce la résistance à la sécheresse et aux maladies."
        )
    
    # pH
    if analyse.ph_actuel:
        if analyse.ph_actuel < 5.5:
            messages.append(
                f"⚠️ pH acide ({analyse.ph_actuel}). Envisager un chaulage léger "
                "(500-1000 kg/ha de dolomie) pour améliorer la disponibilité des nutriments."
            )
        elif analyse.ph_actuel > 7.5:
            messages.append(
                f"⚠️ pH alcalin ({analyse.ph_actuel}). Privilégier les engrais organiques "
                "et surveiller la biodisponibilité du fer et du zinc."
            )
    
    # Recommandation spécifique
    type_labels = {
        'aucun': "Aucun engrais nécessaire",
        'organique': "Apport de compost ou fumier bien décomposé",
        'mineral_npk': "Engrais NPK complet",
        'mineral_uree': "Engrais azoté (urée) complété par PK si besoin",
        'mixte': "Approche mixte: fond organique + complément minéral",
    }
    
    messages.append(f"\n💡 Recommandation: {type_labels.get(type_engrais, type_engrais)}")
    
    # Conseils pratiques
    messages.append(
        "\n📋 Conseils d'application:\n"
        "• Répartir l'apport en 2-3 fois si possible\n"
        "• Privilégier l'apport local (compost) avant montée prix intrants\n"
        "• Couvrir les engrais azotés pour limiter volatilisation\n"
        "• Adapter selon prévisions pluviométriques"
    )
    
    return "\n".join(messages)


def _generer_actions_prioritaires(analyse: AnalyseNutriments, type_engrais: str) -> list[dict]:
    """Génère la liste des actions prioritaires avec niveau d'urgence."""
    
    actions = []
    
    # Action 1: Fertilisation
    if type_engrais != 'aucun':
        urgence = 'haute' if analyse.score_fertilite < 0.5 else 'moyenne'
        actions.append({
            'action': 'Procéder à l\'apport d\'engrais recommandé dans les 2 semaines',
            'urgence': urgence,
            'type': 'fertilisation',
        })
    
    # Action 2: Correction pH si nécessaire
    if analyse.ph_actuel:
        if analyse.ph_actuel < 5.5:
            actions.append({
                'action': 'Planifier chaulage léger (dolomie) avant prochain semis',
                'urgence': 'moyenne',
                'type': 'amenagement',
            })
        elif analyse.ecart_ph and analyse.ecart_ph > 1.0:
            actions.append({
                'action': 'Surveiller symptômes de carences (pH éloigné du optimal)',
                'urgence': 'basse',
                'type': 'surveillance',
            })
    
    # Action 3: Déficits spécifiques
    if analyse.deficit_azote > 50:
        actions.append({
            'action': 'Urgence azote: apport fractionné immédiat + couverture',
            'urgence': 'haute',
            'type': 'fertilisation',
        })
    
    if analyse.deficit_phosphore > 40:
        actions.append({
            'action': 'Favoriser engrais phosphatés localisés au semis',
            'urgence': 'moyenne',
            'type': 'fertilisation',
        })
    
    # Action 4: Suivi
    actions.append({
        'action': 'Planifier nouvelle analyse sol dans 3-6 mois',
        'urgence': 'basse',
        'type': 'planification',
    })
    
    return actions


def generer_recommandation(
    historique_sol: HistoriqueSol,
    culture_cible: Optional[ProduitAgricole] = None,
    sauvegarder: bool = True,
) -> RecommandationFertilisation:
    """
    Génère une recommandation de fertilisation complète à partir d'un historique sol.
    
    Args:
        historique_sol: Instance HistoriqueSol avec N-P-K et pH
        culture_cible: Culture pour laquelle la recommandation est faite (optionnel)
        sauvegarder: Si True, persiste la recommandation en base
    
    Returns:
        Instance RecommandationFertilisation (sauvegardée ou non)
    """
    # Déterminer la culture de référence
    culture_key = 'mil'  # default
    culture_nom = "culture générale"
    
    if culture_cible:
        culture_nom = culture_cible.nom
        # Mapping nom produit -> clé besoins
        nom_lower = culture_cible.nom.lower()
        for key in BESOINS_NPK.keys():
            if key in nom_lower:
                culture_key = key
                break
    elif historique_sol.culture_precedente:
        nom_lower = historique_sol.culture_precedente.nom.lower()
        for key in BESOINS_NPK.keys():
            if key in nom_lower:
                culture_key = key
                break
    
    # Analyse
    analyse = _calculer_deficits(historique_sol, culture_key)
    
    # Suggestion engrais
    type_engrais, quantite = _suggere_type_engrais(analyse)
    
    # Messages et actions
    message = _generer_message(analyse, type_engrais, culture_nom)
    actions = _generer_actions_prioritaires(analyse, type_engrais)
    
    # Calcul confiance (basée sur qualité données)
    confiance = 0.75
    if historique_sol.azote_ppm is None or historique_sol.phosphore_ppm is None:
        confiance -= 0.15
    if historique_sol.ph is None:
        confiance -= 0.10
    if analyse.score_fertilite < 0.3:
        confiance -= 0.10  # Moins confiant si sol très pauvre
    confiance = max(0.4, min(0.95, confiance))
    
    recommandation = RecommandationFertilisation(
        historique_sol=historique_sol,
        culture_cible=culture_cible,
        type_engrais_conseille=type_engrais,
        quantite_kg_ha=quantite,
        message_explication=message,
        priorite_actions=actions,
        confiance_score=Decimal(str(confiance)),
    )
    
    if sauvegarder:
        with transaction.atomic():
            recommandation.save()
        logger.info(
            "Recommandation fertilisation créée: ferme=%s, culture=%s, type=%s",
            historique_sol.ferme.nom,
            culture_nom,
            type_engrais,
        )
    
    return recommandation


def obtenir_derniere_recommandation(
    ferme_id: str,
    culture: Optional[ProduitAgricole] = None,
) -> Optional[RecommandationFertilisation]:
    """
    Récupère la dernière recommandation active pour une ferme.
    """
    qs = RecommandationFertilisation.objects.filter(
        historique_sol__ferme_id=ferme_id,
    ).select_related('historique_sol', 'culture_cible')
    
    if culture:
        qs = qs.filter(culture_cible=culture)
    
    return qs.first()


def generer_recommandation_rapide(
    n_ppm: float,
    p_ppm: float,
    k_ppm: float,
    ph: Optional[float] = None,
    culture: str = "culture générale",
) -> ConseilFertilisation:
    """
    Version standalone pour recommandations rapides sans historique sol en base.
    """
    # Créer un historique temporaire
    class MockHistorique:
        def __init__(self, n, p, k, ph):
            self.azote_ppm = n
            self.phosphore_ppm = p
            self.potassium_ppm = k
            self.ph = ph
            self.culture_precedente = None
    
    mock = MockHistorique(n_ppm, p_ppm, k_ppm, ph)
    
    # Mapping culture
    culture_key = 'mil'
    for key in BESOINS_NPK.keys():
        if key in culture.lower():
            culture_key = key
            break
    
    analyse = _calculer_deficits(mock, culture_key)
    type_engrais, quantite = _suggere_type_engrais(analyse)
    message = _generer_message(analyse, type_engrais, culture)
    actions = _generer_actions_prioritaires(analyse, type_engrais)
    
    return ConseilFertilisation(
        type_engrais=type_engrais,
        quantite_kg_ha=quantite,
        message=message,
        actions_prioritaires=actions,
        confiance=analyse.score_fertilite,
    )
