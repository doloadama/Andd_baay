import logging
import os
import base64
import hashlib
from datetime import timedelta
from types import SimpleNamespace

import requests
from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail

from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db import transaction
from django.db.models.functions import Coalesce
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import (
    DemandeAccesFerme,
    Depense,
    Ferme,
    HistoriqueRendement,
    HistoriqueSol,
    Investissement,
    MembreFerme,
    PrevisionRecolte,
    ProduitAgricole,
    Profile,
    Projet,
    ProjetProduit,
    Recette,
)
from .messaging_contract import build_recruitment_status_event_v1

logger = logging.getLogger(__name__)


def _format_fcfa_montant(amount: Decimal) -> str:
    if amount is None:
        return "0"
    try:
        n = int(amount.quantize(Decimal("1")))
    except Exception:
        n = int(amount)
    return f"{n:,}".replace(",", "\u202f")


def investissement_montant_expr():
    """Expression ORM : coût/ha × ha (culture ou projet) + autres frais."""
    return ExpressionWrapper(
        F("cout_par_hectare")
        * Coalesce(
            F("projet_produit__superficie_allouee"),
            F("projet__superficie"),
        )
        + Coalesce(F("autres_frais"), Value(Decimal("0"))),
        output_field=DecimalField(max_digits=24, decimal_places=2),
    )


def total_investissements_projet(projet_id):
    agg = (
        Investissement.objects.filter(projet_id=projet_id)
        .aggregate(t=Coalesce(Sum(investissement_montant_expr()), Value(Decimal("0"))))
    )
    return agg["t"] or Decimal("0")


def total_recettes_projet(projet_id):
    agg = Recette.objects.filter(projet_id=projet_id).aggregate(
        t=Coalesce(Sum("montant_total"), Value(Decimal("0")))
    )
    return agg["t"] or Decimal("0")


def calculer_kpis_financiers_globaux(projet_ids) -> dict:
    """KPIs financiers agrégés sur un ensemble de projets — 3 requêtes SQL fixes.

    Évite le N+1 quand le dashboard / une vue récap a besoin du total des recettes
    et des coûts sur tous les projets accessibles. Pour le détail par projet
    (cout/unité, ROI individuel, etc.), utiliser calculer_kpis_financiers_projet.
    """
    if not projet_ids:
        return {
            "total_recettes": Decimal("0"),
            "total_couts": Decimal("0"),
        }
    inv_expr = investissement_montant_expr()
    inv_total = Investissement.objects.filter(projet_id__in=projet_ids).aggregate(
        t=Coalesce(Sum(inv_expr), Value(Decimal("0")))
    )["t"]
    dep_total = Depense.objects.filter(projet_id__in=projet_ids).aggregate(
        t=Coalesce(Sum("montant"), Value(Decimal("0")))
    )["t"]
    rec_total = Recette.objects.filter(projet_id__in=projet_ids).aggregate(
        t=Coalesce(Sum("montant_total"), Value(Decimal("0")))
    )["t"]
    return {
        "total_recettes": rec_total or Decimal("0"),
        "total_couts": (inv_total or Decimal("0")) + (dep_total or Decimal("0")),
    }


def calculer_kpis_financiers_par_projet(projet_ids) -> dict[str, dict]:
    """
    KPIs financiers calculés *en masse* par projet (évite le N+1).

    Retour:
      { "<projet_id>": { total_recettes, total_depenses, total_depenses_lignes_investissement,
                        total_depenses_fiche_simple, total_investissements, total_couts,
                        benefice_net, roi_pct } }

    Note: cette version n'inclut pas les champs coûteux/non essentiels au dashboard
    (quantité récoltée, coût de revient/unité, prédictions prévisionnelles).
    """
    if not projet_ids:
        return {}

    inv_expr = investissement_montant_expr()
    inv_rows = (
        Investissement.objects.filter(projet_id__in=projet_ids)
        .values("projet_id")
        .annotate(
            total_lignes_investissement=Coalesce(Sum(inv_expr), Value(Decimal("0"))),
            total_investissements=Coalesce(
                Sum(inv_expr, filter=Q(categorie="materiel")),
                Value(Decimal("0")),
            ),
            total_depenses_lignes_investissement=Coalesce(
                Sum(inv_expr, filter=~Q(categorie="materiel")),
                Value(Decimal("0")),
            ),
        )
    )
    dep_rows = (
        Depense.objects.filter(projet_id__in=projet_ids)
        .values("projet_id")
        .annotate(total_depenses_fiche_simple=Coalesce(Sum("montant"), Value(Decimal("0"))))
    )
    rec_rows = (
        Recette.objects.filter(projet_id__in=projet_ids)
        .values("projet_id")
        .annotate(total_recettes=Coalesce(Sum("montant_total"), Value(Decimal("0"))))
    )

    out: dict[str, dict] = {
        str(pid): {
            "total_recettes": Decimal("0"),
            "total_depenses": Decimal("0"),
            "total_depenses_lignes_investissement": Decimal("0"),
            "total_depenses_fiche_simple": Decimal("0"),
            "total_investissements": Decimal("0"),
            "total_couts": Decimal("0"),
            "benefice_net": Decimal("0"),
            "roi_pct": None,
        }
        for pid in projet_ids
    }

    for r in inv_rows:
        k = str(r["projet_id"])
        block = out.get(k)
        if block is None:
            continue
        block["total_investissements"] = r["total_investissements"] or Decimal("0")
        block["total_depenses_lignes_investissement"] = (
            r["total_depenses_lignes_investissement"] or Decimal("0")
        )
        block["_total_lignes_investissement_fcfa"] = (
            r["total_lignes_investissement"] or Decimal("0")
        )

    for r in dep_rows:
        k = str(r["projet_id"])
        block = out.get(k)
        if block is None:
            continue
        block["total_depenses_fiche_simple"] = r["total_depenses_fiche_simple"] or Decimal("0")

    for r in rec_rows:
        k = str(r["projet_id"])
        block = out.get(k)
        if block is None:
            continue
        block["total_recettes"] = r["total_recettes"] or Decimal("0")

    for k, block in out.items():
        total_lignes_inv = block.pop("_total_lignes_investissement_fcfa", Decimal("0")) or Decimal("0")
        dep_fiche = block["total_depenses_fiche_simple"] or Decimal("0")
        dep_lignes = block["total_depenses_lignes_investissement"] or Decimal("0")
        rec = block["total_recettes"] or Decimal("0")

        total_depenses = dep_lignes + dep_fiche
        total_couts = total_lignes_inv + dep_fiche
        benefice = rec - total_couts
        roi = (benefice / total_couts * Decimal("100")) if total_couts else None

        block["total_depenses"] = total_depenses
        block["total_couts"] = total_couts
        block["benefice_net"] = benefice
        block["roi_pct"] = roi

    return out


def _safe_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _quantite_recoltee_projet(projet_id) -> Decimal:
    agg = ProjetProduit.objects.filter(projet_id=projet_id).aggregate(
        q=Coalesce(Sum("rendement_final"), Value(Decimal("0")))
    )
    return agg["q"] or Decimal("0")


def _prediction_revenue_proxy(projet_id) -> Decimal:
    total = Decimal("0")
    rows = (
        PrevisionRecolte.objects.filter(projet_id=projet_id)
        .select_related("projet_produit__produit")
    )
    for prev in rows:
        predicted_qty = (
            _safe_decimal(prev.rendement_estime_min)
            + _safe_decimal(prev.rendement_estime_max)
        ) / Decimal("2")
        produit = prev.projet_produit.produit if prev.projet_produit_id else None
        prix = produit.prix_par_kg if produit and produit.prix_par_kg is not None else Decimal("0")
        total += predicted_qty * prix
    return total


def calculer_kpis_financiers_projet(projet_id) -> dict:
    """
    KPIs financiers réels d'un projet (dashboard, API mobile, clôture).

    Formules (FCFA) :
    - Somme des lignes ``Investissement`` : total_lignes_investissement (= tout matériel + hors matériel).
    - Total ``Depense`` (fiches projet) ajouté au dénominateur de coût total.
    - Total coûts = total_lignes_investissement + total_depenses_fiche_simple.
    - total_depenses : charges d'exploitation = lignes inv hors « matériel » + fiches ``Depense``.
    - Investissements matériels : catégorie « matériel » sur les lignes inv.
    - Bénéfice net = Total recettes − Total coûts ; ROI % = Bénéfice net / Total coûts × 100.
    """
    inv_expr = investissement_montant_expr()
    inv_aggr = Investissement.objects.filter(projet_id=projet_id).aggregate(
        total_lignes_investissement=Coalesce(Sum(inv_expr), Value(Decimal("0"))),
        total_investissements=Coalesce(
            Sum(inv_expr, filter=Q(categorie="materiel")),
            Value(Decimal("0")),
        ),
        total_depenses_lignes_investissement=Coalesce(
            Sum(inv_expr, filter=~Q(categorie="materiel")),
            Value(Decimal("0")),
        ),
    )
    dep_aggr = Depense.objects.filter(projet_id=projet_id).aggregate(
        sf=Coalesce(Sum("montant"), Value(Decimal("0")))
    )
    total_depenses_fiche = dep_aggr["sf"] or Decimal("0")
    total_recettes = total_recettes_projet(projet_id)
    total_lignes_inv = inv_aggr["total_lignes_investissement"] or Decimal("0")
    total_depenses_inv = inv_aggr["total_depenses_lignes_investissement"] or Decimal("0")
    total_investissements = inv_aggr["total_investissements"] or Decimal("0")
    total_depenses_combinees = total_depenses_inv + total_depenses_fiche
    total_couts = total_lignes_inv + total_depenses_fiche
    benefice_net = total_recettes - total_couts
    roi = (benefice_net / total_couts * Decimal("100")) if total_couts else None
    quantite_recoltee = _quantite_recoltee_projet(projet_id)
    cout_revient_unite = (
        (total_depenses_combinees / quantite_recoltee) if quantite_recoltee else None
    )
    recettes_prevues = _prediction_revenue_proxy(projet_id)
    ecart_previsionnel = total_recettes - recettes_prevues
    ecart_previsionnel_pct = (
        ecart_previsionnel / recettes_prevues * Decimal("100")
        if recettes_prevues
        else None
    )

    return {
        "projet_id": str(projet_id),
        "total_recettes": total_recettes,
        "total_depenses": total_depenses_combinees,
        "total_depenses_lignes_investissement": total_depenses_inv,
        "total_depenses_fiche_simple": total_depenses_fiche,
        "total_lignes_investissement_fcfa": total_lignes_inv,
        "total_investissements": total_investissements,
        "total_couts": total_couts,
        "benefice_net": benefice_net,
        "roi_pct": roi,
        "quantite_recoltee": quantite_recoltee,
        "cout_revient_unite": cout_revient_unite,
        "recettes_prevues": recettes_prevues,
        "ecart_previsionnel": ecart_previsionnel,
        "ecart_previsionnel_pct": ecart_previsionnel_pct,
    }


def cloturer_projet(projet_id) -> dict:
    """
    Clôture comptable : statut « clôturé », verrouillage des lignes ``Investissement`` et
    des fiches ``Depense`` associées au projet.

    Prérequis : projet « fini ». Idempotent : re-verrouille les lignes restées ouvertes
    et renvoie les KPI.
    """
    from django.utils import timezone as _tz

    with transaction.atomic():
        projet = Projet.objects.select_for_update().get(pk=projet_id)
        becoming = projet.statut != Projet.STATUT_CLOTURE
        if becoming:
            if projet.statut != "fini":
                raise ValidationError(
                    "Clôture comptable impossible : le projet doit d'abord être au statut « Fini » "
                    "(travaux et récolte terminés). Les écritures comptables restent ouvertes tant "
                    "qu'il n'est pas « Clôturé »."
                )
            projet.statut = Projet.STATUT_CLOTURE
        date_fin_ajoutee = False
        if not projet.date_fin:
            projet.date_fin = _tz.localdate()
            date_fin_ajoutee = True
        to_update = []
        if becoming:
            to_update.append("statut")
        if date_fin_ajoutee:
            to_update.append("date_fin")
        if to_update:
            projet.save(update_fields=to_update)
        Investissement.objects.filter(projet=projet, verrouille=False).update(
            verrouille=True,
            date_verrouillage=_tz.now(),
        )
        Depense.objects.filter(projet=projet, verrouille=False).update(
            verrouille=True,
            date_verrouillage=_tz.now(),
        )
        kpis = calculer_kpis_financiers_projet(projet.id)
    return {"projet": projet, "kpis": kpis, "etait_deja_cloture": not becoming}


def check_budget_status(projet_id):
    """
    Compare la somme des investissements (montant par ligne : ha culture ou projet)
    au budget_alloue du projet (FCFA).
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

    total = total_investissements_projet(projet_id)

    budget_val = budget or Decimal("0")
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
        "projet_nom": projet.nom,
    }


def check_projet_produit_budget_status(projet_produit_id):
    """Budget optionnel par culture (ProjetProduit.budget_alloue)."""
    pp = (
        ProjetProduit.objects.filter(pk=projet_produit_id)
        .select_related("projet", "produit")
        .only("id", "budget_alloue", "projet__nom", "produit__nom")
        .first()
    )
    if not pp:
        return {"ok": False, "applicable": False}
    if pp.budget_alloue is None:
        return {
            "ok": True,
            "applicable": False,
            "over_budget": False,
            "produit_nom": pp.produit.nom if pp.produit_id else "",
            "projet_nom": pp.projet.nom,
        }

    total = (
        Investissement.objects.filter(projet_produit_id=projet_produit_id).aggregate(
            t=Coalesce(Sum(investissement_montant_expr()), Value(Decimal("0")))
        )["t"]
        or Decimal("0")
    )
    budget_val = pp.budget_alloue or Decimal("0")
    over = total > budget_val
    depassement = (total - budget_val) if over else Decimal("0")
    label = f"{pp.produit.nom} — {pp.projet.nom}"
    return {
        "ok": True,
        "applicable": True,
        "over_budget": over,
        "total_investi": total,
        "budget": budget_val,
        "depassement": depassement,
        "depassement_display": _format_fcfa_montant(depassement),
        "projet_line_label": label,
    }

# ─────────────────────────────────────────────────────────────────────────────
#  Tables de données pour estimer_rendement_ia()
#  (module-level pour éviter de les reconstruire à chaque appel)
# ─────────────────────────────────────────────────────────────────────────────

# Rendements typiques (kg/ha) des petits exploitants en Afrique de l'Ouest.
# Utilisés uniquement quand le catalogue produit ET l'historique local sont absents.
# Sources : FAO/FAOSTAT moyennes Sénégal/Mali/Burkina 2015-2023.
_RENDEMENT_FALLBACK_KG_HA = {
    'arachide':  1000.0,   'riz':       2000.0,   'mil':        750.0,
    'millet':     750.0,   'sorgho':    1000.0,   'maïs':      2000.0,
    'mais':      2000.0,   'fonio':      700.0,   'blé':       2500.0,
    'ble':       2500.0,   'niébé':      500.0,   'niebe':      500.0,
    'soja':      1500.0,   'coton':      800.0,   'sésame':     500.0,
    'sesame':     500.0,   'tournesol': 1000.0,   'manioc':   10000.0,
    'igname':   12000.0,   'patate':    8000.0,   'taro':      5000.0,
    'tomate':   18000.0,   'oignon':   20000.0,   'piment':    4000.0,
    'gombo':     5000.0,   'aubergine': 10000.0,  'chou':     15000.0,
    'laitue':   12000.0,   'carotte':  15000.0,   'concombre': 15000.0,
    'pastèque': 20000.0,   'pasteque': 20000.0,   'melon':    15000.0,
    'bissap':     700.0,   'moringa':   4000.0,   'gingembre': 7000.0,
}

# Sols inadaptés par culture (mot-clé → frozenset de TypeSol).
# La 1ère correspondance dans le nom de la culture est utilisée.
# Cultures absentes = pas de règle sol (tolérance inconnue ou culture non-sol).
# TypeSol choices : 'Dior', 'Deck', 'Deck-Dior', 'Sablonneux', 'Latéritique'
_REGLES_SOL = {
    # ── Céréales ──────────────────────────────────────────────────────────
    'arachide':   frozenset({'Deck', 'Latéritique'}),
    'riz':        frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'maïs':       frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'mais':       frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'mil':        frozenset({'Deck', 'Latéritique'}),
    'millet':     frozenset({'Deck', 'Latéritique'}),
    'sorgho':     frozenset({'Sablonneux', 'Latéritique'}),
    'fonio':      frozenset({'Deck', 'Latéritique'}),
    'blé':        frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'ble':        frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    # ── Légumineuses ──────────────────────────────────────────────────────
    'niébé':      frozenset({'Latéritique'}),
    'niebe':      frozenset({'Latéritique'}),
    'soja':       frozenset({'Sablonneux', 'Latéritique'}),
    'haricot':    frozenset({'Sablonneux', 'Latéritique'}),
    'lentille':   frozenset({'Sablonneux', 'Latéritique'}),
    'voandzou':   frozenset({'Latéritique'}),
    'pois':       frozenset({'Latéritique'}),
    # ── Cultures de rente / oléagineuses ──────────────────────────────────
    'coton':      frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'sésame':     frozenset({'Deck', 'Latéritique'}),
    'sesame':     frozenset({'Deck', 'Latéritique'}),
    'tournesol':  frozenset({'Sablonneux', 'Latéritique'}),
    'canne':      frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'tabac':      frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    # ── Tubercules & racines ───────────────────────────────────────────────
    'manioc':     frozenset({'Latéritique'}),
    'igname':     frozenset({'Deck', 'Latéritique'}),
    'patate':     frozenset({'Deck', 'Latéritique'}),
    'taro':       frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'pomme de':   frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    # ── Maraîchage – légumes fruits ───────────────────────────────────────
    'tomate':     frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'oignon':     frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'piment':     frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'poivron':    frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'aubergine':  frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'gombo':      frozenset({'Latéritique'}),
    'concombre':  frozenset({'Latéritique'}),
    'courgette':  frozenset({'Latéritique'}),
    'pastèque':   frozenset({'Deck', 'Latéritique'}),
    'pasteque':   frozenset({'Deck', 'Latéritique'}),
    'melon':      frozenset({'Deck', 'Latéritique'}),
    'gingembre':  frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'curcuma':    frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    # ── Maraîchage – légumes feuilles / racines ────────────────────────────
    'chou':       frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'laitue':     frozenset({'Dior', 'Sablonneux', 'Latéritique'}),
    'carotte':    frozenset({'Deck', 'Latéritique'}),
    'navet':      frozenset({'Deck', 'Latéritique'}),
    'betterave':  frozenset({'Deck', 'Latéritique'}),
    'ail':        frozenset({'Deck', 'Latéritique'}),
    'échalote':   frozenset({'Deck', 'Latéritique'}),
    'echalote':   frozenset({'Deck', 'Latéritique'}),
}

# Mots-clés identifiant les cultures pérennes (arbres, lianes, palmiers).
# → Pas de pénalité "semis tardif" ; confiance plafonnée à 55 %.
_MOTS_CLÉS_PÉRENNE = frozenset({
    'palmier', 'cacao', 'café', 'cafe', 'karité', 'karite', 'hévéa', 'hevea',
    'mangue', 'banane', 'agrumes', 'orange', 'citron', 'noix de coco', 'anacarde',
    'cajou', 'goyave', 'avocat', 'datte', 'tamarin', 'baobab', 'neem', 'jatropha',
    'vanille', 'maracuja', 'passion', 'macadamia', 'pitaya', 'dragon',
    'poivre noir', 'ananas', 'papaye', 'goyave', 'karité',
})

# Mots-clés identifiant les cultures en milieu contrôlé (bassin, salle).
# → Règles sol et eau non applicables ; confiance plafonnée à 40 %.
_MOTS_CLÉS_MILIEU_CONTRÔLÉ = frozenset({
    'spiruline', 'champignon', 'pleurote',
})


def _categorie_culture(nom_produit: str) -> str:
    """
    Retourne la catégorie agronomique de la culture :
      'contrôlé' — hors-sol ou en bassin (spiruline, champignons...)
      'pérenne'  — arbre ou liane pluriannuel (mangue, cacao, palmier...)
      'annuelle' — culture à cycle court/moyen en plein champ (défaut)
    """
    nom = nom_produit.lower()
    for mot in _MOTS_CLÉS_MILIEU_CONTRÔLÉ:
        if mot in nom:
            return 'contrôlé'
    for mot in _MOTS_CLÉS_PÉRENNE:
        if mot in nom:
            return 'pérenne'
    return 'annuelle'


def _rendement_fallback_par_nom(nom_produit: str) -> float:
    """
    Rendement de référence (kg/ha) par nom de culture.
    Utilisé uniquement quand ni le catalogue ni l'historique local ne sont disponibles.
    """
    nom = nom_produit.lower()
    for mot_cle, valeur in _RENDEMENT_FALLBACK_KG_HA.items():
        if mot_cle in nom:
            return valeur
    return 1000.0  # ultime fallback générique


def estimer_rendement_ia(projet_produit):
    """
    Estime dynamiquement le rendement d'une culture selon des critères agronomiques.

    Corrections v3 (2026-05) :
      - Applicable à toutes les cultures du catalogue (60+ espèces) :
          • Règles sol couvrant ~35 cultures via _REGLES_SOL
          • Cultures pérennes (arbre/liane) : pas de pénalité semis tardif,
            confiance plafonnée à 55 %
          • Cultures en milieu contrôlé (spiruline, champignons) : règles
            sol et eau désactivées, confiance plafonnée à 40 %
      - Intervalle élargi (±16–40 %) proportionnel au stress réel
      - Confiance de base à 50 % ; plafond renforcé selon la qualité des données
      - Calibration prioritaire sur HistoriqueRendement local (5 ans)
      - Fallback par espèce (_RENDEMENT_FALLBACK_KG_HA) si aucune donnée
    """
    produit = projet_produit.produit
    projet = projet_produit.projet
    localite = projet.localite

    nom_produit = produit.nom.lower()
    categorie = _categorie_culture(produit.nom)
    est_pérenne = categorie == 'pérenne'
    est_contrôlé = categorie == 'contrôlé'

    # ── 1. Rendement de base ─────────────────────────────────────────────────
    # Priorité : historique local (5 ans) > historique régional (10 ans)
    #          > catalogue produit > fallback par espèce
    historique_local = list(
        HistoriqueRendement.objects.filter(localite=localite, produit=produit)
        .order_by('-annee')[:5]
    )
    n_historique_local = len(historique_local)

    historique_regional = []
    n_historique_regional = 0
    if not historique_local and localite and localite.region_id:
        historique_regional = list(
            HistoriqueRendement.objects.filter(
                localite__region_id=localite.region_id, produit=produit
            ).order_by('-annee')[:10]
        )
        n_historique_regional = len(historique_regional)

    if historique_local:
        _rend = [float(h.rendement_reel_kg_ha) for h in historique_local]
        rendement_base = sum(_rend) / len(_rend)
        source_rendement = 'historique_local'
    elif historique_regional:
        _rend = [float(h.rendement_reel_kg_ha) for h in historique_regional]
        rendement_base = sum(_rend) / len(_rend)
        source_rendement = 'historique_regional'
    elif produit.rendement_potentiel_max or produit.rendement_moyen:
        rendement_base = float(produit.rendement_potentiel_max or produit.rendement_moyen)
        source_rendement = 'catalogue'
    else:
        rendement_base = _rendement_fallback_par_nom(produit.nom)
        source_rendement = 'fallback'

    superficie = float(projet_produit.superficie_allouee or 1.0)
    rendement_total_base = rendement_base * superficie

    penalite = 0.0
    bonus = 0.0
    confiance = 50.0    # Base honnête pour un système à règles non validé

    if source_rendement == 'historique_local':
        confiance += 15.0   # Données réelles locales — ancrage empirique fort
    elif source_rendement == 'historique_regional':
        confiance += 10.0   # Données régionales — moins précis que local
    elif source_rendement == 'catalogue':
        confiance += 5.0    # Potentiel produit connu mais non localisé

    # ── 2. Règles sol ────────────────────────────────────────────────────────
    # Désactivées pour les cultures hors-sol (spiruline, champignons).
    sol_inadapte = False
    if not est_contrôlé and localite and localite.type_sol:
        confiance += 5.0    # Sol connu → les règles peuvent s'appliquer
        sol = localite.type_sol

        for mot_cle, sols_nok in _REGLES_SOL.items():
            if mot_cle in nom_produit:
                if sol in sols_nok:
                    sol_inadapte = True
                break   # première correspondance uniquement

    if sol_inadapte:
        penalite += 0.20
        confiance -= 10.0

    # ── 3. Eau (Pluviométrie + Irrigation) ──────────────────────────────────
    # Désactivée pour les cultures en milieu contrôlé.
    if not est_contrôlé:
        besoin_eau = produit.besoin_eau_mm or 0
        pluie_moyenne = (localite.pluviometrie_moyenne or 0) if localite else 0

        if besoin_eau > 0 and pluie_moyenne < besoin_eau:
            if projet.type_irrigation == 'Aucune':
                penalite += 0.40
                confiance -= 15.0
            else:
                if projet.type_irrigation == 'Goutte-à-goutte':
                    confiance += 8.0
                else:
                    confiance += 4.0

    # ── 4. Semis tardif ──────────────────────────────────────────────────────
    # Non applicable aux cultures pérennes (arbres) ni aux cultures contrôlées.
    if not est_pérenne and not est_contrôlé and projet_produit.date_semis:
        mois_semis = projet_produit.date_semis.month
        if produit.saison == 'Hivernage' and mois_semis >= 8:
            penalite += 0.15
            confiance -= 8.0

    # ── 5. Fertilisation ─────────────────────────────────────────────────────
    if projet.type_engrais != 'Aucun':
        if projet.type_engrais == 'Mixte':
            bonus += 0.15
            confiance += 6.0
        elif 'Minéral' in projet.type_engrais:
            bonus += 0.12
            confiance += 4.0
        elif projet.type_engrais == 'Organique':
            bonus += 0.08
            confiance += 4.0    # Bénéfique mais effet plus lent que le minéral

    # ── 5b. Association de cultures ──────────────────────────────────────────
    # La présence d'une légumineuse dans le même projet apporte de l'azote
    # aux céréales voisines via la fixation symbiotique (rhizobium).
    _LÉGUMINEUSES_ASSOC = frozenset({'niébé', 'niebe', 'arachide', 'soja', 'mucuna'})
    autres_noms = list(
        projet.projet_produits.exclude(pk=projet_produit.pk)
        .values_list('produit__nom', flat=True)
    )
    legumineuse_associee = any(
        any(leg in n.lower() for leg in _LÉGUMINEUSES_ASSOC)
        for n in autres_noms if n
    )
    if legumineuse_associee:
        bonus += 0.10       # fixation azote → +10% rendement de la culture associée
        confiance += 5.0

    # ── 5c. Observation terrain (état végétatif, P2.2) ───────────────────────
    # Note de l'agriculteur sur l'état réel de la culture (1=très mauvais, 5=excellent).
    # Prime toute règle théorique : +12 pts de confiance car observation directe.
    _MULT_OBS = {1: 0.55, 2: 0.78, 3: 1.00, 4: 1.18, 5: 1.38}
    etat_veg = getattr(projet_produit, 'etat_vegetatif', None)
    if etat_veg is not None and etat_veg in _MULT_OBS:
        bonus_obs = _MULT_OBS[etat_veg] - 1.0   # delta pondéré (positif ou négatif)
        if bonus_obs >= 0:
            bonus += bonus_obs
        else:
            penalite += abs(bonus_obs)
        confiance += 12.0   # observation terrain → certitude accrue quelle que soit la note

    # ── 6. Rendement cible ───────────────────────────────────────────────────
    modificateur = max(0.1, 1.0 - penalite + bonus)
    rendement_cible = rendement_total_base * modificateur

    # ── 6b. Correcteur de biais calibré ──────────────────────────────────────
    # Compense les sur/sous-estimations systématiques observées sur les projets
    # clôturés. Facteur = 1/(1+biais%) — neutre (1.0) si n < 5 observations.
    from baay.services.prediction_accuracy import get_correcteurs_biais_par_culture
    correcteur_biais = 1.0
    try:
        for mot, facteur in get_correcteurs_biais_par_culture().items():
            if mot in nom_produit:
                rendement_cible *= facteur
                correcteur_biais = facteur
                confiance += 3.0   # modèle calibré → légère hausse de confiance
                break
    except Exception:
        pass    # cache indisponible (tests, CI) → non bloquant

    # ── 7. Intervalle de prédiction ──────────────────────────────────────────
    if penalite >= 0.40:
        variance = 0.40
    elif penalite >= 0.20:
        variance = 0.30
    elif penalite > 0:
        variance = 0.25
    else:
        variance = 0.20

    if source_rendement == 'historique_local':
        variance *= 0.80    # Données locales réelles → intervalle le plus serré
    elif source_rendement == 'historique_regional':
        variance *= 0.90    # Données régionales → légèrement plus serré que défaut

    # ── 7b. Progression phénologique (P2.1) ──────────────────────────────────
    # Plus la culture approche de la maturité, plus la prédiction est précise :
    # la variance se resserre et la confiance augmente au fil du cycle.
    # Progression 0→1 (semis→récolte). Sans date_semis ou cycle : pas d'ajustement.
    progression_cycle = 0.0
    cycle_jours = produit.cycle_culture_jours or produit.duree_avant_recolte
    if projet_produit.date_semis and cycle_jours and cycle_jours > 0:
        from datetime import date as _date
        jours_ecoules = (_date.today() - projet_produit.date_semis).days
        progression_cycle = min(1.0, max(0.0, jours_ecoules / cycle_jours))
        # Variance : ±20–40% → ±12–24% à maturité (réduction max 40%)
        variance *= max(0.60, 1.0 - progression_cycle * 0.40)
        # Confiance : +12 pts maximum à maturité
        confiance += progression_cycle * 12.0

    rendement_min = max(0.0, rendement_cible * (1.0 - variance))
    rendement_max = rendement_cible * (1.0 + variance)

    # ── 8. Plafonds de confiance selon la qualité des données et la catégorie ─
    if source_rendement == 'fallback':
        confiance = min(confiance, 45.0)    # Aucune donnée réelle disponible
    if est_pérenne:
        confiance = min(confiance, 55.0)    # Modèle non calibré pour l'arboriculture
    if est_contrôlé:
        confiance = min(confiance, 40.0)    # Sol/eau hors-sujet → forte incertitude

    # ── 9. Date de récolte prévue ────────────────────────────────────────────
    date_recolte = None
    cycle = produit.cycle_culture_jours or produit.duree_avant_recolte
    if projet_produit.date_semis and cycle:
        date_recolte = projet_produit.date_semis + timedelta(days=cycle)

    confiance_finale = min(100.0, max(0.0, confiance))

    # ── Vecteur de features (usage interne P4 — collecte silencieuse pour ML) ─
    _features = {
        # Contexte pédologique et hydrique
        'sol_type': (localite.type_sol if localite else None),
        'sol_inadapte': sol_inadapte,
        'pluie_moyenne': float((localite.pluviometrie_moyenne or 0) if localite else 0),
        'besoin_eau': float(produit.besoin_eau_mm or 0),
        'deficit_hydrique': (
            not est_contrôlé
            and bool(produit.besoin_eau_mm)
            and float(produit.besoin_eau_mm or 0) > float((localite.pluviometrie_moyenne or 0) if localite else 0)
            and getattr(projet, 'type_irrigation', 'Aucune') == 'Aucune'
        ),
        'type_irrigation': getattr(projet, 'type_irrigation', None),
        # Calendrier cultural
        'mois_semis': (projet_produit.date_semis.month if projet_produit.date_semis else None),
        'saison': getattr(produit, 'saison', None),
        # Agronomie
        'type_engrais': getattr(projet, 'type_engrais', None),
        'superficie': float(projet_produit.superficie_allouee or 1.0),
        'categorie_culture': categorie,
        'source_rendement': source_rendement,
        # Modificateurs calculés
        'penalite': round(penalite, 4),
        'bonus': round(bonus, 4),
        'variance': round(variance, 4),
        'confiance': round(confiance_finale, 2),
        # Qualité des données historiques
        'n_historique_local': n_historique_local,
        'n_historique_regional': n_historique_regional,
        # Associations agronomiques
        'cultures_associees': [n for n in autres_noms if n],
        # Champs remplis par étapes ultérieures (P2, P5)
        'etat_vegetatif': etat_veg,                         # observation terrain 1–5
        'progression_cycle': round(progression_cycle, 4),  # 0.0–1.0
        'correcteur_biais': round(correcteur_biais, 6),
        'ndvi': None,                   # rempli en P5.3
        'pluie_reelle_mm': None,        # rempli en P5.1
    }

    return {
        'min': round(rendement_min, 2),
        'max': round(rendement_max, 2),
        'confiance': confiance_finale,
        'date_recolte_prevue': date_recolte,
        'source_rendement': source_rendement,
        'categorie_culture': categorie,
        '_features': _features,
    }


def get_prevision_affichee_projet(projet):
    """
    Vue agrégée des prévisions d'un projet (une ligne par ProjetProduit possible).
    Retourne un seul PrevisionRecolte si une seule entrée, sinon un SimpleNamespace
    avec les mêmes attributs pour les gabarits.
    """
    if projet is None or not projet.pk:
        return None
    # Utilise le prefetch cache si disponible (évite une requête par projet sur les listes).
    pref = getattr(projet, "_prefetched_objects_cache", None) or {}
    if "previsions" in pref:
        rows = sorted(list(pref.get("previsions") or []), key=lambda r: r.date_prediction, reverse=True)
    else:
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

    Alimente également PrevisionFeatures (collecte silencieuse pour P4 ML)
    avec le vecteur _features retourné par estimer_rendement_ia().
    """
    from .models import PrevisionFeatures  # import local pour éviter les circulaires

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

    # ── P4 : Collecte silencieuse du vecteur de features ────────────────────
    features_data = resultats.get("_features")
    if features_data:
        try:
            PrevisionFeatures.objects.update_or_create(
                prevision=prediction,
                defaults={"features": features_data},
            )
        except Exception as exc:
            logger.warning(
                "Impossible de sauvegarder PrevisionFeatures pour %s : %s",
                prediction.pk, exc,
            )

    return prediction


def compute_previsions_for_projet(projet_id: str) -> dict:
    """Service: compute PrevisionRecolte for each ProjetProduit of a projet and
    update the denormalized Projet.rendement_estime field. Returns summary dict.
    """
    with transaction.atomic():
        projet = Projet.objects.select_related("ferme").get(pk=projet_id)
        pps = list(
            ProjetProduit.objects.filter(projet=projet).select_related(
                "produit", "projet", "projet__localite"
            )
        )
        for pp in pps:
            update_prediction_for_projet_produit(pp)

        prevs = list(PrevisionRecolte.objects.filter(projet=projet))
        total_min = sum(p.rendement_estime_min for p in prevs) if prevs else 0
        total_max = sum(p.rendement_estime_max for p in prevs) if prevs else 0
        projet.rendement_estime = (total_min + total_max) / 2 if prevs else None
        projet.save(update_fields=["rendement_estime"])  

    return {
        "projet": projet,
        "total_min": total_min,
        "total_max": total_max,
        "count_pp": len(pps),
    }


# =====================
# Météo (OpenWeatherMap)
# =====================
def get_weather_by_coords(lat, lon, cache_key_suffix: str = "") -> dict:
    """Fetches weather from OpenWeatherMap for any lat/lon pair."""
    api_key = getattr(settings, "OPENWEATHER_API_KEY", None) or os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "error": "api_key_absente"}

    cache_key = f"weather:coords:{round(float(lat),3)}:{round(float(lon),3)}{cache_key_suffix}"
    cached = cache.get(cache_key)
    if cached is not None:
        return {"ok": True, "data": cached}

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric", "lang": "fr"}
    try:
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code != 200:
            return {"ok": False, "error": f"http_{resp.status_code}"}
        raw = resp.json() or {}
        weather = (raw.get("weather") or [{}])[0]
        w = {
            "temperature": (raw.get("main") or {}).get("temp"),
            "humidite": (raw.get("main") or {}).get("humidity"),
            "description": weather.get("description"),
            "icone": weather.get("icon"),
        }
        try:
            ttl_min = int(getattr(settings, "WEATHER_CACHE_TTL_MINUTES", 30))
        except Exception:
            ttl_min = 30
        cache.set(cache_key, w, timeout=max(60, ttl_min * 60))
        return {"ok": True, "data": w}
    except Exception as e:
        logger.error("Erreur appel OpenWeather", exc_info=True)
        return {"ok": False, "error": "exception"}


def get_weather_data(ferme_id: str) -> dict:
    """Retourne la meteo temps reel d'une ferme via OpenWeatherMap."""
    ferme = (
        Ferme.objects
        .only("id", "latitude", "longitude")
        .filter(pk=ferme_id)
        .first()
    )
    if not ferme:
        return {"ok": False, "error": "ferme_introuvable"}

    lat = ferme.latitude
    lon = ferme.longitude
    if lat is None or lon is None:
        return {"ok": False, "error": "coords_absentes"}

    api_key = getattr(settings, "OPENWEATHER_API_KEY", None) or os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "error": "api_key_absente"}

    cache_key = f"weather:ferme:{ferme_id}:{round(float(lat),3)}:{round(float(lon),3)}"
    cached = cache.get(cache_key)
    if cached is not None:
        return {"ok": True, "data": cached}

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
        "lang": "fr",
    }
    try:
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code != 200:
            return {"ok": False, "error": f"http_{resp.status_code}"}
        raw = resp.json() or {}
        weather = (raw.get("weather") or [{}])[0]
        w = {
            "temperature": (raw.get("main") or {}).get("temp"),
            "humidite": (raw.get("main") or {}).get("humidity"),
            "description": weather.get("description"),
            "icone": weather.get("icon"),
        }
        try:
            ttl_min = int(getattr(settings, "WEATHER_CACHE_TTL_MINUTES", 30))
        except Exception:
            ttl_min = 30
        cache.set(cache_key, w, timeout=max(60, ttl_min * 60))
        return {"ok": True, "data": w}
    except Exception as e:
        logger.error("Erreur appel OpenWeather", exc_info=True)
        return {"ok": False, "error": "exception"}


# =====================
# Recrutement / Demandes
# =====================
def transition_demande_acces(demande_id: str, nouveau_statut: str, role: str = "ouvrier", peut_gerer_membres: bool = False) -> dict:
    """Transition d'etat pour DemandeAccesFerme.

    Si approuvee, cree MembreFerme et notifie l'utilisateur.
    """
    if nouveau_statut not in {"en_attente", "approuvee", "refusee"}:
        raise ValidationError({"statut": "Statut invalide."})
    if role not in {"manager", "technicien", "ouvrier", "consultant", "invite"}:
        role = "ouvrier"

    with transaction.atomic():
        demande = (
            DemandeAccesFerme.objects.select_for_update()
            .select_related("ferme", "utilisateur__user")
            .filter(pk=demande_id)
            .first()
        )
        if not demande:
            return {"ok": False, "error": "demande_introuvable"}

        created_membership = False
        if demande.statut == nouveau_statut:
            return {"ok": True, "demande": demande, "created_membership": False}

        if nouveau_statut == "approuvee":
            membre, created_membership = MembreFerme.objects.get_or_create(
                ferme=demande.ferme,
                utilisateur=demande.utilisateur,
                defaults={"role": role, "peut_gerer_membres": bool(peut_gerer_membres)},
            )
            if not created_membership:
                membre.role = role
                membre.peut_gerer_membres = bool(peut_gerer_membres)
                membre.save(update_fields=["role", "peut_gerer_membres"])

        demande.statut = nouveau_statut
        from django.utils import timezone as _tz
        demande.date_traitement = _tz.now()
        demande.save(update_fields=["statut", "date_traitement"])

    _notify_demande_acces_user(demande, nouveau_statut)
    return {"ok": True, "demande": demande, "created_membership": bool(created_membership)}


def create_demande_acces_ferme(ferme: Ferme, utilisateur: Profile) -> DemandeAccesFerme:
    """Cree une demande apres validation anti-doublon et anti-membre."""
    demande = DemandeAccesFerme(
        ferme=ferme,
        utilisateur=utilisateur,
        code=ferme.code_acces,
    )
    demande.full_clean()
    demande.save()
    return demande


def _notify_demande_acces_user(demande: DemandeAccesFerme, statut: str) -> None:
    """Notification best-effort : websocket si disponible, email sinon/en plus."""
    try:
        layer = get_channel_layer()
        payload = build_recruitment_status_event_v1(demande, statut)
        async_to_sync(layer.group_send)(f"inbox_{demande.utilisateur.id}", payload)
    except Exception:
        logger.warning("Notification recrutement Channels ignoree", exc_info=True)

    email = demande.utilisateur.user.email
    if not email:
        return
    if statut == "approuvee":
        subject = f"Votre demande d'acces a {demande.ferme.nom} a ete approuvee"
        message = (
            f"Bonjour {demande.utilisateur.user.username},\n\n"
            f"Votre demande d'acces a la ferme {demande.ferme.nom} a ete approuvee.\n"
            "Vous pouvez desormais y acceder depuis Andd Baay."
        )
    elif statut == "refusee":
        subject = f"Votre demande d'acces a {demande.ferme.nom} a ete refusee"
        message = (
            f"Bonjour {demande.utilisateur.user.username},\n\n"
            f"Votre demande d'acces a la ferme {demande.ferme.nom} n'a pas ete acceptee."
        )
    else:
        return
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@anddbaay.local"),
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception:
        logger.warning("Email recrutement non envoye a %s", email, exc_info=True)


# =====================
# Médias Cloudinary — livraison optimisée (mobile / faible bande passante)
# =====================


class CloudinaryPreset:
    """Noms usuels pour `cloudinary_sahara_url` / gabarits HTML."""

    THUMB = "thumb"
    LIST = "list"
    DASHBOARD = "dashboard"
    DETAIL = "detail"
    REPORT = "report"


_SAHARA_IMAGE_PRESETS = {
    CloudinaryPreset.THUMB: {
        "width": 280,
        "height": 280,
        "crop": "fill",
        "gravity": "auto",
        "fetch_format": "auto",
        "quality": "auto",
    },
    CloudinaryPreset.LIST: {
        "width": 480,
        "height": 480,
        "crop": "limit",
        "fetch_format": "auto",
        "quality": "auto",
    },
    CloudinaryPreset.DASHBOARD: {
        "width": 768,
        "height": 432,
        "crop": "limit",
        "fetch_format": "auto",
        "quality": "auto",
    },
    CloudinaryPreset.DETAIL: {
        "width": 1280,
        "height": 1280,
        "crop": "limit",
        "fetch_format": "auto",
        "quality": "auto",
    },
    CloudinaryPreset.REPORT: {
        "width": 2000,
        "height": 2000,
        "crop": "limit",
        "fetch_format": "auto",
        "quality": "auto",
    },
}


def cloudinary_direct_url(media_value) -> str:
    """URL de livraison par défaut (sans transformation catalogue)."""
    if not media_value:
        return ""
    try:
        u = getattr(media_value, "url", None)
        if u:
            return u
    except Exception:
        pass
    raw = getattr(media_value, "name", None) or str(media_value)
    return raw.strip() if raw else ""


def cloudinary_sahara_url(
    media_value,
    preset: str = CloudinaryPreset.LIST,
    *,
    dpr_auto: bool = True,
) -> str:
    """
    URL avec f_auto et q_auto (via options Cloudinary).
    Pour les fichiers ``resource_type=raw`` (PDF…) : fallback sur l’URL directe sans transformation image.
    """
    if not media_value:
        return ""

    try:
        from baay.cloudinary_helpers import public_id_and_type as _pid_rt
        from django.conf import settings as dj_settings

        from cloudinary import utils as cu
    except Exception:
        return cloudinary_direct_url(media_value)

    if not getattr(dj_settings, "CLOUDINARY_ACTIVE", False):
        return cloudinary_direct_url(media_value)

    pid, rt = _pid_rt(media_value)
    if not pid:
        return cloudinary_direct_url(media_value)

    if rt != "image":
        return cloudinary_direct_url(media_value)

    transforms = dict(_SAHARA_IMAGE_PRESETS.get(preset, _SAHARA_IMAGE_PRESETS[CloudinaryPreset.LIST]))
    if dpr_auto:
        transforms.setdefault("dpr", "auto")
    kw = dict(transforms)
    kw["secure"] = True
    try:
        url, _unused = cu.cloudinary_url(pid, **kw)
        return url or cloudinary_direct_url(media_value)
    except Exception:
        return cloudinary_direct_url(media_value)


def cloudinary_img_lazy_attrs(media_value, preset: str = CloudinaryPreset.LIST, *, alt: str = ""):
    """
    Attributs HTML conseillés pour chargement différé (dashboard mobile).
    Exemple gabarit : ``<img {...|cloudinary_img_lazy_attrs:pp.image,'thumb',alt='Plant'} />``
    (avec un filtre custom ou en Python : ``attr=cloudinary_img_lazy_attrs(...)`` puis spread).
    """
    src = cloudinary_sahara_url(media_value, preset=preset)
    attrs = {"src": src, "loading": "lazy", "decoding": "async", "alt": alt}
    sizes = getattr(settings, "CLOUDINARY_SRCSET_WIDTHS", (320, 480, 640, 960))
    if not media_value:
        return attrs

    try:
        from baay.cloudinary_helpers import public_id_and_type as _pid_rt
        from django.conf import settings as dj_settings

        from cloudinary import utils as cu
    except Exception:
        return attrs

    if not getattr(dj_settings, "CLOUDINARY_ACTIVE", False):
        return attrs

    pid, rt = _pid_rt(media_value)
    if not pid or rt != "image":
        return attrs

    # srcset responsive : toujours "limit" (pas de crop) + f_auto/q_auto
    srcset_parts = []
    try:
        for w in sizes or ():
            try:
                w_int = int(w)
            except Exception:
                continue
            if w_int <= 0:
                continue
            transforms = dict(
                _SAHARA_IMAGE_PRESETS.get(preset, _SAHARA_IMAGE_PRESETS[CloudinaryPreset.LIST])
            )
            transforms["width"] = w_int
            transforms["crop"] = transforms.get("crop") or "limit"
            transforms.setdefault("fetch_format", "auto")
            transforms.setdefault("quality", "auto")
            transforms.setdefault("dpr", "auto")
            transforms["secure"] = True
            url, _unused = cu.cloudinary_url(pid, **transforms)
            if url:
                srcset_parts.append(f"{url} {w_int}w")
    except Exception:
        srcset_parts = []

    if srcset_parts:
        attrs["srcset"] = ", ".join(srcset_parts)
        # Sizes minimaliste: plein écran mobile, puis cartes sur desktop
        attrs["sizes"] = "(max-width: 768px) 100vw, 640px"
    else:
        attrs["srcset"] = ""
        attrs["sizes"] = ""

    return attrs


def upload_static_to_cloudinary(
    static_path: str,
    public_id: str,
    *,
    overwrite: bool = False,
    invalidate: bool = True,
) -> dict:
    """
    Upload a file from ``baay/static/`` to Cloudinary.

    Args:
        static_path: Relative path inside ``baay/static/`` (e.g., "images/image2.jpg").
        public_id: Desired public_id on Cloudinary (e.g., "auth/login-bg").
        overwrite: Replace existing resource.
        invalidate: Invalidate CDN cache.

    Returns:
        dict with ``url``, ``public_id``, ``secure_url``, or raises on failure.
    """
    from pathlib import Path

    try:
        import cloudinary
        import cloudinary.uploader
    except Exception as exc:
        raise RuntimeError("Cloudinary SDK not installed") from exc

    if not getattr(settings, "CLOUDINARY_ACTIVE", False):
        raise RuntimeError("CLOUDINARY_URL not configured")

    base_dir = Path(__file__).resolve().parent.parent
    full_path = base_dir / "baay" / "static" / static_path

    if not full_path.exists():
        raise FileNotFoundError(f"Static file not found: {full_path}")

    result = cloudinary.uploader.upload(
        str(full_path),
        public_id=public_id,
        folder="andd-baayi",
        resource_type="image",
        overwrite=overwrite,
        invalidate=invalidate,
        use_filename=False,
    )

    return {
        "url": result.get("url"),
        "secure_url": result.get("secure_url"),
        "public_id": result.get("public_id"),
    }


# ────────────────────────────────────────────────────────────────────────────
# Context processor helpers (auth backgrounds)
# ────────────────────────────────────────────────────────────────────────────

def get_auth_background_urls() -> dict:
    """
    Returns Cloudinary URLs for auth pages backgrounds.
    Falls back to static URLs if Cloudinary not configured.
    """
    from django.templatetags.static import static

    # Local static paths (fallback)
    login_bg_static = static("images/image2.jpg")
    signup_bg_static = static("images/image.jpg")

    if not getattr(settings, "CLOUDINARY_ACTIVE", False):
        return {
            "login_bg_url": login_bg_static,
            "signup_bg_url": signup_bg_static,
        }

    # Try to get Cloudinary URLs from settings
    login_bg = getattr(settings, "LOGIN_BG_CLOUDINARY_URL", None)
    signup_bg = getattr(settings, "SIGNUP_BG_CLOUDINARY_URL", None)

    return {
        "login_bg_url": login_bg or login_bg_static,
        "signup_bg_url": signup_bg or signup_bg_static,
    }


def product_placeholder_data_uri(product_name: str) -> str:
    """
    Lightweight per-product image (SVG data URI).
    Deterministic colors based on product name, optimized for low bandwidth.
    """
    name = (product_name or "Produit").strip()
    initials = "".join([p[0] for p in name.split()[:2] if p])[:2].upper() or "P"
    h = hashlib.sha256(name.encode("utf-8")).hexdigest()
    c1 = f"#{h[0:6]}"
    c2 = f"#{h[6:12]}"
    text = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540" role="img" aria-label="{text}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{c1}"/>
      <stop offset="1" stop-color="{c2}"/>
    </linearGradient>
    <filter id="s" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#000" flood-opacity="0.25"/>
    </filter>
  </defs>
  <rect width="960" height="540" rx="36" fill="url(#g)"/>
  <g filter="url(#s)">
    <rect x="56" y="56" width="848" height="428" rx="28" fill="rgba(255,255,255,0.14)" stroke="rgba(255,255,255,0.22)"/>
  </g>
  <text x="96" y="170" font-family="system-ui, -apple-system, Segoe UI, Roboto, Arial" font-weight="800" font-size="64" fill="rgba(255,255,255,0.95)">{initials}</text>
  <text x="96" y="250" font-family="system-ui, -apple-system, Segoe UI, Roboto, Arial" font-weight="700" font-size="38" fill="rgba(255,255,255,0.9)">{text}</text>
  <text x="96" y="310" font-family="system-ui, -apple-system, Segoe UI, Roboto, Arial" font-weight="600" font-size="22" fill="rgba(255,255,255,0.75)">Suivi des plants</text>
</svg>"""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


# ─── Soil Ledger ─────────────────────────────────────────────────────────────

_PH_TOLERANT_ACIDS = {"Manioc", "Arachide", "Patate douce", "Ananas"}  # pH < 6
_PH_ALKALINE_SENSITIVE = {"Riz", "Blé", "Orge"}  # pH > 7.5 → déconseillé
_LEGUMES = {"Arachide", "Niébé", "Soja", "Haricot"}  # fixateurs azote
_HIGH_K_DEMAND = {"Banane", "Tomate", "Pomme de terre", "Patate douce"}  # K exigeants

_SEUIL_K_BAS = Decimal("80")   # ppm — en dessous : déconseiller cultures K-exigeantes
_SEUIL_N_BAS = Decimal("20")   # ppm — en dessous : favoriser légumineuses


def suggerer_semis_saison_suivante(ferme_id) -> dict:
    """
    Analyse le dernier enregistrement ``HistoriqueSol`` de la ferme et retourne
    une suggestion de culture pour la saison suivante.

    Retourne ::

        {
            "suggestion": ProduitAgricole | None,
            "raison": str,
            "confiance": int,   # 0-100
            "alertes": list[str],
        }
    """
    derniere = (
        HistoriqueSol.objects.filter(ferme_id=ferme_id)
        .select_related("culture_precedente")
        .order_by("-date_mesure")
        .first()
    )

    if derniere is None:
        return {
            "suggestion": None,
            "raison": "Aucune analyse de sol enregistrée pour cette ferme.",
            "confiance": 0,
            "alertes": [],
        }

    alertes: list[str] = []
    exclusions: set[str] = set()
    preferences: list[str] = []
    raisons: list[str] = []
    confiance = 40  # base

    ph = derniere.ph
    azote = derniere.azote_ppm
    potassium = derniere.potassium_ppm
    culture_prec = derniere.culture_precedente

    # ── pH ──────────────────────────────────────────────────────────────────
    if ph is not None:
        confiance += 15
        if ph < Decimal("5.5"):
            alertes.append(f"pH acide ({ph}) — amendement calcique recommandé.")
            preferences.extend(_PH_TOLERANT_ACIDS)
            raisons.append("pH acide : cultures tolérantes choisies")
        elif ph > Decimal("7.5"):
            alertes.append(f"pH alcalin ({ph}) — apport de soufre possible.")
            exclusions.update(_PH_ALKALINE_SENSITIVE)
            raisons.append("pH alcalin : céréales sensibles exclues")
        else:
            raisons.append(f"pH optimal ({ph})")

    # ── Azote ────────────────────────────────────────────────────────────────
    if azote is not None:
        confiance += 10
        if azote < _SEUIL_N_BAS:
            alertes.append(f"Azote bas ({azote} ppm) — légumineuse recommandée.")
            preferences.extend(_LEGUMES)
            raisons.append("Azote faible : légumineuse fixatrice favorisée")

    # ── Potassium ────────────────────────────────────────────────────────────
    if potassium is not None:
        confiance += 10
        if potassium < _SEUIL_K_BAS:
            alertes.append(f"Potassium bas ({potassium} ppm) — éviter cultures K-exigeantes.")
            exclusions.update(_HIGH_K_DEMAND)
            raisons.append("Potassium faible : cultures exigeantes exclues")

    # ── Rotation culturale ───────────────────────────────────────────────────
    if culture_prec is not None:
        confiance += 10
        prec_nom = culture_prec.nom
        if prec_nom in _LEGUMES:
            raisons.append(f"Rotation après légumineuse ({prec_nom}) : céréale conseillée")
            preferences.append("Mil")
            preferences.append("Sorgho")
            preferences.append("Maïs")
        else:
            exclusions.add(prec_nom)
            raisons.append(f"Rotation : {prec_nom} exclu pour éviter l'épuisement")

    # ── Sélection du candidat ────────────────────────────────────────────────
    suggestion: ProduitAgricole | None = None

    if preferences:
        # Recherche stricte par ordre de préférence
        for nom_pref in preferences:
            candidat = (
                ProduitAgricole.objects.filter(nom__iexact=nom_pref)
                .exclude(nom__in=exclusions)
                .first()
            )
            if candidat:
                suggestion = candidat
                break

    if suggestion is None:
        # Fallback : n'importe quelle culture hors exclusions
        suggestion = (
            ProduitAgricole.objects.exclude(nom__in=exclusions).order_by("nom").first()
        )

    confiance = min(confiance, 95)

    return {
        "suggestion": suggestion,
        "raison": " ; ".join(raisons) if raisons else "Analyse standard.",
        "confiance": confiance,
        "alertes": alertes,
    }
