"""
Service d'évaluation de la précision du modèle de prédictions de récolte.

Compare les prévisions produites par `estimer_rendement_ia()` (min/max, kg)
avec les rendements réels enregistrés dans `ProjetProduit.rendement_final`
(rempli lors de la clôture d'un projet).

Métriques calculées
-------------------
- **MAPE** (Mean Absolute Percentage Error) : erreur absolue moyenne en %
  ⟹ < 20 % = bon, < 10 % = excellent
- **Taux de couverture** : % de cas où le rendement réel se trouve dans
  l'intervalle [rendement_estime_min, rendement_estime_max]
  ⟹ > 70 % = bon
- **Biais** : erreur relative moyenne signée
  ⟹ proche de 0 = équilibré, > 0 = sur-estimation systématique
"""

import logging
from decimal import Decimal

from django.db.models import Q

logger = logging.getLogger(__name__)


def evaluer_precision_modele(ferme_ids=None):
    """
    Calcule les métriques de précision du modèle de prédictions de récolte.

    Parameters
    ----------
    ferme_ids : list[uuid] | None
        Si fourni, restreint l'analyse aux fermes spécifiées.
        Si None, analyse l'ensemble des projets clôturés accessibles.

    Returns
    -------
    dict avec les clés :
        n               : int    — nombre d'observations exploitables
        mape            : float  — MAPE globale en %, ou None
        coverage_pct    : float  — taux de couverture en %, ou None
        biais           : float  — biais moyen en %, ou None (+ = sur-estim.)
        par_culture     : dict   — mêmes métriques par nom de culture
        avertissements  : list[str]
    """
    from baay.models import ProjetProduit  # évite import circulaire en top-level

    qs = (
        ProjetProduit.objects.filter(
            rendement_final__isnull=False,
            prevision__isnull=False,
            projet__statut__in=["fini", "cloture"],
        )
        .select_related(
            "prevision",
            "produit",
            "projet__ferme",
        )
    )

    if ferme_ids:
        qs = qs.filter(projet__ferme_id__in=ferme_ids)

    avertissements = []
    mape_items = []
    bias_items = []
    covered_items = []
    par_culture = {}  # {nom_produit: {mape_items, bias_items, covered_items}}

    for pp in qs:
        actual = float(pp.rendement_final or 0)
        prev = pp.prevision

        if actual <= 0 or prev is None:
            continue

        pred_min = float(prev.rendement_estime_min or 0)
        pred_max = float(prev.rendement_estime_max or 0)
        pred_mid = (pred_min + pred_max) / 2.0

        if pred_mid <= 0:
            continue

        mape_item = abs(actual - pred_mid) / actual * 100.0
        bias_item = (pred_mid - actual) / actual * 100.0
        covered = pred_min <= actual <= pred_max

        mape_items.append(mape_item)
        bias_items.append(bias_item)
        covered_items.append(covered)

        # Breakdown par culture
        nom = pp.produit.nom if pp.produit else "Inconnu"
        if nom not in par_culture:
            par_culture[nom] = {"mape": [], "bias": [], "covered": []}
        par_culture[nom]["mape"].append(mape_item)
        par_culture[nom]["bias"].append(bias_item)
        par_culture[nom]["covered"].append(covered)

    n = len(mape_items)

    # Avertissements
    if n == 0:
        avertissements.append(
            "Aucun projet clôturé avec rendement réel et prévision liée. "
            "Renseignez ProjetProduit.rendement_final lors de la clôture des projets."
        )
    elif n < 5:
        avertissements.append(
            f"Échantillon très petit (n={n}). Les métriques ne sont pas statistiquement fiables."
        )

    def _mean(lst):
        return sum(lst) / len(lst) if lst else None

    def _pct_true(lst):
        return sum(1 for v in lst if v) / len(lst) * 100.0 if lst else None

    # Résultats par culture
    par_culture_agg = {}
    for nom, data in par_culture.items():
        par_culture_agg[nom] = {
            "n": len(data["mape"]),
            "mape": _mean(data["mape"]),
            "coverage_pct": _pct_true(data["covered"]),
            "biais": _mean(data["bias"]),
        }

    return {
        "n": n,
        "mape": _mean(mape_items),
        "coverage_pct": _pct_true(covered_items),
        "biais": _mean(bias_items),
        "par_culture": par_culture_agg,
        "avertissements": avertissements,
    }


def qualifier_mape(mape):
    """Retourne un label qualitatif pour une valeur de MAPE."""
    if mape is None:
        return "inconnu"
    if mape < 10:
        return "excellent"
    if mape < 20:
        return "bon"
    if mape < 35:
        return "acceptable"
    return "à améliorer"


def qualifier_coverage(pct):
    """Retourne un label qualitatif pour le taux de couverture."""
    if pct is None:
        return "inconnu"
    if pct >= 80:
        return "excellent"
    if pct >= 70:
        return "bon"
    if pct >= 50:
        return "acceptable"
    return "à améliorer"
