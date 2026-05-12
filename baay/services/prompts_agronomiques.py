"""
Prompts et templates pour l'Expert Agronome IA
Pilier 1: Intelligence Agronomique
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ContexteExploitation:
    """Données contextuelles pour les recommandations agronomiques."""
    localite: str
    region: str
    pays: str = "Sénégal"
    produit_nom: str = ""
    age_plant: int = 0
    cycle_estime: int = 0
    budget_disponible: float = 0.0


@dataclass
class DonneesSol:
    """Données d'analyse de sol."""
    n_mg_kg: float
    p_mg_kg: float
    k_mg_kg: float
    ph: float
    matieres_organiques_pourcent: Optional[float] = None
    texture: Optional[str] = None
    date_analyse: Optional[str] = None


# =============================================================================
# TEMPLATES DE PROMPT
# =============================================================================

PROMPT_EXPERT_AGRONOME = """# ROLE
Tu es l'Expert Agronome IA de la plateforme "Andd_baay", spécialisé dans l'agriculture sahélienne et tropicale (contexte : {pays}). Ton objectif est de transformer des données brutes en conseils actionnables pour optimiser le rendement et la santé des sols.

# CONTEXTE TECHNIQUE
L'utilisateur gère une ferme avec les paramètres suivants :
- Localisation : {localite} ({region}, {pays})
- Culture actuelle : {produit_nom}
- Stade de la culture : {age_plant} jours (Cycle total : {cycle_estime} jours)
- Budget restant : {budget_disponible:,.0f} FCFA

# DONNÉES SOL (Analyse du {date_analyse})
- Azote (N) : {n_mg_kg} mg/kg
- Phosphore (P) : {p_mg_kg} mg/kg
- Potassium (K) : {k_mg_kg} mg/kg
- pH : {ph}
{texture_info}
{mo_info}

# NORMES DE RÉFÉRENCE POUR {produit_nom_upper}
Besoins nutritionnels typiques :
- N : {n_min}-{n_max} mg/kg (optimal)
- P : {p_min}-{p_max} mg/kg (optimal)
- K : {k_min}-{k_max} mg/kg (optimal)
- pH : {ph_min}-{ph_max} (optimal)

# OBJECTIFS DE LA RÉPONSE
1. ANALYSE : Interprète les valeurs N-P-K par rapport aux besoins spécifiques du/de la {produit_nom}.
2. ALERTE : Identifie toute carence critique ou déséquilibre du pH.
3. RECOMMANDATION : Propose des actions concrètes (engrais bio ou minéraux, amendements) en tenant compte du budget de {budget_disponible:,.0f} FCFA.
4. CALENDRIER : Indique si c'est le bon moment pour intervenir selon l'âge de la plante ({age_plant}j / {cycle_estime}j).

# CONTRAINTES DE TON (STRICT)
- Réponse concise et structurée en points clés.
- Utilise un langage simple, évite le jargon complexe sauf si nécessaire.
- Priorise les solutions locales et accessibles au {pays} (ex: fumier, compost, NPK 15-15-15, urée, chaux agricole).
- Format de sortie : Markdown propre.

# STRUCTURE DE SORTIE OBLIGATOIRE

## 📊 État de votre sol
[Bref diagnostic N-P-K + pH. Indique clairement si chaque élément est: ✅ Suffisant | ⚠️ Faible | 🔴 Critique]

## 🌱 Conseil de Fertilisation Immédiat
[Action prioritaire spécifique à faire maintenant, adaptée au stade {age_plant}j]
- Type d'engrais recommandé
- Dosage approximatif pour {superficie} ha
- Fréquence d'application

## ⚠️ Vigilance & Risques à {age_plant}j
[Maladies ou stress potentiels selon le stade actuel et les carences identifiées]
- Risque phytosanitaire lié aux carences
- Conseil préventif

## 💰 Optimisation Budget ({budget_disponible:,.0f} FCFA)
[Comment maximiser l'impact avec le budget disponible]
- Option économique (bio/local)
- Option rapide (minéral)
- Coût estimé par kg/ha

## 📅 Calendrier
[Le moment est-il propice pour intervenir ?]
- ✅ Oui, urgence | ⏳ Attendre X jours | ❌ Trop tard pour cette action

---
Génère maintenant la recommandation agronomique personnalisée:"""


# =============================================================================
# NORMES NUTRITIONNELLES PAR CULTURE (Sahel/Tropical)
# =============================================================================

NORMES_CULTURES = {
    "mil": {
        "n": {"min": 40, "max": 80, "unite": "mg/kg"},
        "p": {"min": 15, "max": 30, "unite": "mg/kg"},
        "k": {"min": 120, "max": 200, "unite": "mg/kg"},
        "ph": {"min": 5.5, "max": 7.0},
        "notes": "Tolérant à la pauvreté, mais réactif à la fertilisation NPK",
    },
    "mais": {
        "n": {"min": 80, "max": 150, "unite": "mg/kg"},
        "p": {"min": 20, "max": 40, "unite": "mg/kg"},
        "k": {"min": 150, "max": 250, "unite": "mg/kg"},
        "ph": {"min": 6.0, "max": 7.0},
        "notes": "Grand consommateur d'azote, sensible à l'aluminium en sol acide",
    },
    "arachide": {
        "n": {"min": 30, "max": 60, "unite": "mg/kg"},
        "p": {"min": 25, "max": 50, "unite": "mg/kg"},
        "k": {"min": 100, "max": 180, "unite": "mg/kg"},
        "ph": {"min": 6.0, "max": 7.0},
        "notes": "Fixatrice d'azote, mais besoin élevé en phosphore au début",
    },
    "niebe": {
        "n": {"min": 20, "max": 40, "unite": "mg/kg"},
        "p": {"min": 15, "max": 30, "unite": "mg/kg"},
        "k": {"min": 100, "max": 160, "unite": "mg/kg"},
        "ph": {"min": 5.5, "max": 7.0},
        "notes": "Légumineuse, besoins N faibles grâce à la fixation",
    },
    "sorgho": {
        "n": {"min": 50, "max": 90, "unite": "mg/kg"},
        "p": {"min": 15, "max": 30, "unite": "mg/kg"},
        "k": {"min": 120, "max": 200, "unite": "mg/kg"},
        "ph": {"min": 5.5, "max": 7.5},
        "notes": "Très rustique, tolère sols pauvres mieux que le maïs",
    },
    "riz": {
        "n": {"min": 100, "max": 200, "unite": "mg/kg"},
        "p": {"min": 20, "max": 40, "unite": "mg/kg"},
        "k": {"min": 150, "max": 300, "unite": "mg/kg"},
        "ph": {"min": 5.5, "max": 6.5},
        "notes": "Culture exigeante, préfère sols argileux avec eau stagnante",
    },
    "tomate": {
        "n": {"min": 100, "max": 200, "unite": "mg/kg"},
        "p": {"min": 30, "max": 60, "unite": "mg/kg"},
        "k": {"min": 200, "max": 350, "unite": "mg/kg"},
        "ph": {"min": 6.0, "max": 6.8},
        "notes": "Besoin élevé en potassium pour qualité des fruits",
    },
    "oignon": {
        "n": {"min": 80, "max": 150, "unite": "mg/kg"},
        "p": {"min": 25, "max": 50, "unite": "mg/kg"},
        "k": {"min": 150, "max": 250, "unite": "mg/kg"},
        "ph": {"min": 6.0, "max": 7.0},
        "notes": "Sensibilité à l'acidité, besoin constant d'eau",
    },
}


# =============================================================================
# SOLUTIONS LOCALES DISPONIBLES (Sénégal/Région)
# =============================================================================

SOLUTIONS_LOCALES = {
    "engrais_mineraux": {
        "NPK_15_15_15": {
            "prix_kg_fcfa": 450,
            "fournisseurs": ["Sodéfitex", "GMB", "Distributeurs agréés"],
            "utilisation": "Fertilisation de fond ou maintenance",
        },
        "NPK_10_18_18": {
            "prix_kg_fcfa": 520,
            "fournisseurs": ["Sodéfitex", "Importateurs"],
            "utilisation": "Démarrage cultures exigeantes en P",
        },
        "uree": {
            "prix_kg_fcfa": 380,
            "fournisseurs": ["ICS", "Distributeurs"],
            "utilisation": "Complément azoté rapide (à fractionner)",
        },
        "DAP": {
            "prix_kg_fcfa": 550,
            "fournisseurs": ["Sodéfitex"],
            "utilisation": "Engrais de démarrage riche en P",
        },
    },
    " amendements": {
        "chaux_agricole": {
            "prix_kg_fcfa": 80,
            "fournisseurs": ["Cimenteries locales", "Carrières"],
            "utilisation": "Correction pH < 5.5",
        },
        "fumier_bovin": {
            "prix_kg_fcfa": 25,
            "fournisseurs": ["Éleveurs locaux", "Coopératives"],
            "utilisation": "Amendement organique NPK + MO",
        },
        "compost": {
            "prix_kg_fcfa": 50,
            "fournisseurs": ["GIE compostage", "Production locale"],
            "utilisation": "Amélioration structure sol + libération lente NPK",
        },
        "tourteau_de_coton": {
            "prix_kg_fcfa": 120,
            "fournisseurs": ["Huileries", "SODEFITEX"],
            "utilisation": "Engrais organique riche en N (6-8%)",
        },
    },
    "biofertilisants": {
        "myccorhizes": {
            "prix_unite_fcfa": 15000,
            "fournisseurs": ["ISRA", "Fournisseurs spécialisés"],
            "utilisation": "Amélioration absorption phosphore",
        },
        "biochar": {
            "prix_kg_fcfa": 150,
            "fournisseurs": ["Production artisanale", "ONG"],
            "utilisation": "Rétention eau/nutriments, séquestration carbone",
        },
    },
}


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def generer_prompt_expert(
    contexte: ContexteExploitation,
    sol: DonneesSol,
    superficie_ha: float = 1.0,
) -> str:
    """
    Génère le prompt complet pour l'expert agronome.

    Args:
        contexte: Données contextuelles de l'exploitation
        sol: Données d'analyse de sol
        superficie_ha: Superficie en hectares

    Returns:
        Prompt formaté prêt à envoyer au LLM
    """
    # Récupérer normes pour la culture
    culture_key = contexte.produit_nom.lower().replace("é", "e").replace("è", "e")
    normes = NORMES_CULTURES.get(culture_key, NORMES_CULTURES.get("mil"))

    # Info texture si disponible
    texture_info = ""
    if sol.texture:
        texture_info = f"- Texture : {sol.texture}"

    # Info matières organiques si disponible
    mo_info = ""
    if sol.matieres_organiques_pourcent:
        mo_info = f"- Matières organiques : {sol.matieres_organiques_pourcent}%"

    return PROMPT_EXPERT_AGRONOME.format(
        pays=contexte.pays,
        localite=contexte.localite,
        region=contexte.region,
        produit_nom=contexte.produit_nom,
        produit_nom_upper=contexte.produit_nom.upper(),
        age_plant=contexte.age_plant,
        cycle_estime=contexte.cycle_estime,
        budget_disponible=contexte.budget_disponible,
        n_mg_kg=sol.n_mg_kg,
        p_mg_kg=sol.p_mg_kg,
        k_mg_kg=sol.k_mg_kg,
        ph=sol.ph,
        date_analyse=sol.date_analyse or "Récente",
        superficie=superficie_ha,
        texture_info=texture_info,
        mo_info=mo_info,
        # Normes
        n_min=normes["n"]["min"],
        n_max=normes["n"]["max"],
        p_min=normes["p"]["min"],
        p_max=normes["p"]["max"],
        k_min=normes["k"]["min"],
        k_max=normes["k"]["max"],
        ph_min=normes["ph"]["min"],
        ph_max=normes["ph"]["max"],
    )


def analyser_carences(
    sol: DonneesSol,
    culture: str,
) -> Dict[str, Any]:
    """
    Analyse les carences et excès par rapport aux normes.

    Returns:
        Dict avec statut de chaque nutriment
    """
    culture_key = culture.lower().replace("é", "e").replace("è", "e")
    normes = NORMES_CULTURES.get(culture_key, NORMES_CULTURES.get("mil"))

    def statut_nutriment(valeur, min_val, max_val):
        if valeur < min_val * 0.5:
            return "critique", f"🔴 Carence critique ({(valeur/min_val)*100:.0f}% du minimum)"
        elif valeur < min_val:
            return "faible", f"⚠️ Carence modérée ({(valeur/min_val)*100:.0f}% du minimum)"
        elif valeur > max_val * 1.5:
            return "exces", f"⚠️ Excès possible"
        else:
            return "optimal", f"✅ Niveau optimal"

    n_status, n_msg = statut_nutriment(sol.n_mg_kg, normes["n"]["min"], normes["n"]["max"])
    p_status, p_msg = statut_nutriment(sol.p_mg_kg, normes["p"]["min"], normes["p"]["max"])
    k_status, k_msg = statut_nutriment(sol.k_mg_kg, normes["k"]["min"], normes["k"]["max"])

    # Analyse pH
    if sol.ph < normes["ph"]["min"]:
        ph_status = "acide"
        ph_msg = f"🔴 pH acide ({sol.ph} < {normes['ph']['min']}) - Chaux nécessaire"
    elif sol.ph > normes["ph"]["max"]:
        ph_status = "basique"
        ph_msg = f"⚠️ pH basique ({sol.ph} > {normes['ph']['max']})"
    else:
        ph_status = "optimal"
        ph_msg = f"✅ pH optimal ({sol.ph})"

    return {
        "N": {"valeur": sol.n_mg_kg, "statut": n_status, "message": n_msg},
        "P": {"valeur": sol.p_mg_kg, "statut": p_status, "message": p_msg},
        "K": {"valeur": sol.k_mg_kg, "statut": k_status, "message": k_msg},
        "pH": {"valeur": sol.ph, "statut": ph_status, "message": ph_msg},
        "culture": culture,
        "normes_ref": normes,
    }


def recommander_solutions_budget(
    carences: Dict[str, Any],
    budget: float,
    superficie_ha: float,
) -> Dict[str, Any]:
    """
    Recommande des solutions adaptées au budget.

    Returns:
        Options économique et rapide avec coûts estimés
    """
    options = {
        "economique": [],
        "rapide": [],
        "cout_total_estime": 0.0,
    }

    # Analyser carences
    if carences["N"]["statut"] in ["critique", "faible"]:
        options["economique"].append({
            "produit": "Fumier bovin composté",
            "quantite_kg_ha": 2000,
            "cout_ha": 2000 * SOLUTIONS_LOCALES[" amendements"]["fumier_bovin"]["prix_kg_fcfa"],
            "action": "Épandre 2 tonnes/ha avant pluie",
        })
        options["rapide"].append({
            "produit": "Urée (46% N)",
            "quantite_kg_ha": 50,
            "cout_ha": 50 * SOLUTIONS_LOCALES["engrais_mineraux"]["uree"]["prix_kg_fcfa"],
            "action": "Fractionner: 1/2 au sol, 1/2 couverture",
        })

    if carences["P"]["statut"] in ["critique", "faible"]:
        options["economique"].append({
            "produit": "Compost riche en P (tourteau de coton)",
            "quantite_kg_ha": 500,
            "cout_ha": 500 * SOLUTIONS_LOCALES[" amendements"]["tourteau_de_coton"]["prix_kg_fcfa"],
            "action": "Incorporer en localisé au pied des plants",
        })
        options["rapide"].append({
            "produit": "DAP (18% P)",
            "quantite_kg_ha": 100,
            "cout_ha": 100 * SOLUTIONS_LOCALES["engrais_mineraux"]["DAP"]["prix_kg_fcfa"],
            "action": "Localisé au démarrage",
        })

    if carences["pH"]["statut"] == "acide":
        options["economique"].append({
            "produit": "Biochar",
            "quantite_kg_ha": 500,
            "cout_ha": 500 * SOLUTIONS_LOCALES["biofertilisants"]["biochar"]["prix_kg_fcfa"],
            "action": "Amendement à long terme",
        })
        options["rapide"].append({
            "produit": "Chaux agricole",
            "quantite_kg_ha": 500,
            "cout_ha": 500 * SOLUTIONS_LOCALES[" amendements"]["chaux_agricole"]["prix_kg_fcfa"],
            "action": "Surface ou incorporation profonde",
        })

    # Calcul coût total
    cout_eco = sum(o["cout_ha"] for o in options["economique"]) * superficie_ha
    cout_rapide = sum(o["cout_ha"] for o in options["rapide"]) * superficie_ha

    options["cout_total_estime"] = {
        "economique": cout_eco,
        "rapide": cout_rapide,
        "budget_suffisant_economique": budget >= cout_eco,
        "budget_suffisant_rapide": budget >= cout_rapide,
    }

    return options


# =============================================================================
# EXEMPLE D'UTILISATION
# =============================================================================

if __name__ == "__main__":
    # Exemple d'utilisation
    contexte = ContexteExploitation(
        localite="Thiès",
        region="Thiès",
        produit_nom="Mil",
        age_plant=25,
        cycle_estime=90,
        budget_disponible=75000,
    )

    sol = DonneesSol(
        n_mg_kg=35,
        p_mg_kg=12,
        k_mg_kg=150,
        ph=5.2,
        matieres_organiques_pourcent=1.2,
        date_analyse="2026-05-10",
    )

    # Générer prompt
    prompt = generer_prompt_expert(contexte, sol, superficie_ha=2.5)
    print("=" * 60)
    print("PROMPT GÉNÉRÉ:")
    print("=" * 60)
    print(prompt)

    # Analyse carences
    carences = analyser_carences(sol, "Mil")
    print("\n" + "=" * 60)
    print("ANALYSE CARENCES:")
    print("=" * 60)
    for nutriment, data in carences.items():
        if nutriment not in ["culture", "normes_ref"]:
            print(f"{nutriment}: {data['message']}")
