import logging
from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth.models import User

from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce

from .models import PrevisionRecolte, Profile, Projet

logger = logging.getLogger(__name__)


def _format_fcfa_montant(amount: Decimal) -> str:
    if amount is None:
        return "0"
    try:
        n = int(amount.quantize(Decimal("1")))
    except Exception:
        n = int(amount)
    return f"{n:,}".replace(",", "\u202f")


def check_budget_status(projet_id):
    """
    Compare la somme des investissements (coût/ha × superficie projet + autres frais)
    au budget_alloue du projet (FCFA).

    Retourne un dict avec clés : ok, applicable, over_budget, total_investi, budget,
    depassement, depassement_display, projet_nom.
    """
    projet = (
        Projet.objects.filter(pk=projet_id)
        .only("id", "nom", "budget_alloue", "superficie")
        .first()
    )
    if not projet:
        return {"ok": False, "error": "projet_introuvable"}

    budget = projet.budget_alloue
    if budget is None:
        return {
            "ok": True,
            "applicable": False,
            "over_budget": False,
            "projet_nom": projet.nom,
            "total_investi": None,
            "budget": None,
            "depassement": None,
        }

    total_expr = ExpressionWrapper(
        F("investissement_set__cout_par_hectare") * F("superficie")
        + Coalesce(F("investissement_set__autres_frais"), Value(Decimal("0"))),
        output_field=DecimalField(max_digits=24, decimal_places=2),
    )
    row = (
        Projet.objects.filter(pk=projet_id)
        .annotate(total_investi=Coalesce(Sum(total_expr), Value(Decimal("0"))))
        .values("total_investi", "nom", "budget_alloue")
        .first()
    )

    total = row["total_investi"] or Decimal("0")
    budget_val = row["budget_alloue"] or Decimal("0")
    over = total > budget_val
    depassement = (total - budget_val) if over else Decimal("0")

    return {
        "ok": True,
        "applicable": True,
        "over_budget": over,
        "total_investi": total,
        "budget": budget_val,
        "depassement": depassement,
        "depassement_display": _format_fcfa_montant(depassement),
        "projet_nom": row.get("nom") or projet.nom,
    }

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


def get_prevision_affichee_projet(projet):
    """
    Vue agrégée des prévisions d'un projet (une ligne par ProjetProduit possible).
    Retourne un seul PrevisionRecolte si une seule entrée, sinon un SimpleNamespace
    avec les mêmes attributs pour les gabarits.
    """
    if projet is None or not projet.pk:
        return None
    rows = list(projet.previsions.order_by("-date_prediction"))
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]
    total_min = sum(r.rendement_estime_min for r in rows)
    total_max = sum(r.rendement_estime_max for r in rows)
    confs = [r.indice_confiance for r in rows if r.indice_confiance is not None]
    avg_c = sum(confs) / len(confs) if confs else None
    dates = [r.date_recolte_prevue for r in rows if r.date_recolte_prevue]
    d_prev = max(dates) if dates else None
    return SimpleNamespace(
        rendement_estime_min=total_min,
        rendement_estime_max=total_max,
        indice_confiance=avg_c,
        date_recolte_prevue=d_prev,
    )


def ensure_profile_for_user(user: User) -> Profile:
    """Return a profile for a user, creating it if missing."""
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def update_prediction_for_projet_produit(projet_produit):
    """
    Met à jour ou crée la PrevisionRecolte liée à ce semis (ProjetProduit).
    Une entrée par ligne produit ; le projet est dénormalisé pour requêtes agrégées.
    """
    resultats = estimer_rendement_ia(projet_produit)
    prediction, _ = PrevisionRecolte.objects.update_or_create(
        projet_produit=projet_produit,
        defaults={
            "projet": projet_produit.projet,
            "rendement_estime_min": resultats["min"],
            "rendement_estime_max": resultats["max"],
            "indice_confiance": resultats["confiance"],
            "date_recolte_prevue": resultats["date_recolte_prevue"],
        },
    )
    return prediction
