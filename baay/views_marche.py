# baay/views_marche.py
"""
Vues pour la page des prix agricoles et des alertes marché.

Routes :
  GET /marche/prix/           — liste_prix  (page principale)
  POST /marche/prix/alertes/vue/<pk>/  — marquer_alerte_vue (HTMX)
  GET /marche/prix/graphique/ — graphique_prix_json (données Chart.js)
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Max, Min, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import now
from django.views.decorators.http import require_GET, require_POST

from baay.models import AlertePrix, PrixMarche


# ── Constantes ────────────────────────────────────────────────────────────────

_PERIODE_DEFAUT   = 30   # jours d'historique affichés par défaut
_PAGE_SIZE        = 40   # entrées de prix par page

# Produits proposés dans le filtre (normalisés)
PRODUITS_SURVEILLES = [
    "mil", "sorgho", "maïs", "riz local", "riz importé", "riz",
    "arachide", "niébé", "oignon", "tomate", "patate douce",
    "manioc", "blé", "sucre", "huile de palme", "huile d'arachide",
]

# Régions du Sénégal (pour le filtre)
REGIONS_SENEGAL = [
    "Dakar", "Thiès", "Diourbel", "Kaolack", "Kaffrine",
    "Fatick", "Saint-Louis", "Louga", "Matam", "Tambacounda",
    "Kédougou", "Kolda", "Ziguinchor", "Sédhiou",
]


# ─────────────────────────────────────────────────────────────────────────────
# Page principale
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_GET
def liste_prix(request):
    """
    Page /marche/prix/ — tableau des prix + alertes actives.

    Paramètres GET :
      produit  — filtrer par produit
      region   — filtrer par région
      marche   — filtrer par nom de marché
      periode  — historique en jours (7, 30, 90) ; défaut 30
      page     — numéro de page
    """
    produit_filtre = request.GET.get("produit", "").strip()
    region_filtre  = request.GET.get("region", "").strip()
    marche_filtre  = request.GET.get("marche", "").strip()
    try:
        periode = int(request.GET.get("periode", _PERIODE_DEFAUT))
        if periode not in (7, 30, 90):
            periode = _PERIODE_DEFAUT
    except (ValueError, TypeError):
        periode = _PERIODE_DEFAUT

    date_debut = date.today() - timedelta(days=periode)

    # ── Alertes actives (≤ 7 jours, niveau ≥ warning) ─────────────────────
    alertes = (
        AlertePrix.objects
        .filter(
            date_detection__gte=now() - timedelta(days=7),
            niveau__in=[AlertePrix.NIVEAU_WARNING, AlertePrix.NIVEAU_CRITIQUE],
        )
        .order_by("-date_detection")[:20]
    )

    # ── Données de prix ────────────────────────────────────────────────────
    qs = PrixMarche.objects.filter(date_relevee__gte=date_debut)

    if produit_filtre:
        qs = qs.filter(produit_nom__icontains=produit_filtre)
    if region_filtre:
        qs = qs.filter(region__icontains=region_filtre)
    if marche_filtre:
        qs = qs.filter(marche_nom__icontains=marche_filtre)

    qs = qs.order_by("-date_relevee", "produit_nom", "marche_nom")

    paginator  = Paginator(qs, _PAGE_SIZE)
    page_obj   = paginator.get_page(request.GET.get("page", 1))

    # ── Synthèse par produit (pour les cartes récapitulatives) ────────────
    synthese = _calcul_synthese_produits(date_debut, produit_filtre, region_filtre)

    # ── Listes pour les filtres ────────────────────────────────────────────
    produits_en_base = (
        PrixMarche.objects
        .filter(date_relevee__gte=date_debut)
        .values_list("produit_nom", flat=True)
        .distinct()
        .order_by("produit_nom")
    )
    regions_en_base = (
        PrixMarche.objects
        .filter(date_relevee__gte=date_debut, region__gt="")
        .values_list("region", flat=True)
        .distinct()
        .order_by("region")
    )

    nb_alertes_non_vues = AlertePrix.objects.filter(vue=False, niveau__in=[
        AlertePrix.NIVEAU_WARNING, AlertePrix.NIVEAU_CRITIQUE,
    ]).count()

    return render(request, "marche/prix.html", {
        "page_obj":           page_obj,
        "alertes":            alertes,
        "synthese":           synthese,
        "produits_en_base":   list(produits_en_base),
        "regions_en_base":    list(regions_en_base),
        "produits_surveilles": PRODUITS_SURVEILLES,
        "regions_senegal":    REGIONS_SENEGAL,
        # Filtres actifs
        "produit_filtre":  produit_filtre,
        "region_filtre":   region_filtre,
        "marche_filtre":   marche_filtre,
        "periode":         periode,
        "date_debut":      date_debut,
        "total":           paginator.count,
        "nb_alertes_non_vues": nb_alertes_non_vues,
    })


def _calcul_synthese_produits(
    date_debut: date,
    produit_filtre: str = "",
    region_filtre: str = "",
) -> list[dict]:
    """
    Pour chaque produit (max 10), retourne :
      produit_nom, prix_moyen, prix_min, prix_max, variation_7j (%), nb_points
    """
    qs = PrixMarche.objects.filter(date_relevee__gte=date_debut)
    if produit_filtre:
        qs = qs.filter(produit_nom__icontains=produit_filtre)
    if region_filtre:
        qs = qs.filter(region__icontains=region_filtre)

    grouped = (
        qs.values("produit_nom")
        .annotate(
            prix_moyen=Avg("prix_unitaire"),
            prix_min=Min("prix_unitaire"),
            prix_max=Max("prix_unitaire"),
            nb_points=Count("id"),
        )
        .order_by("produit_nom")[:10]
    )

    result = []
    date_ref = date.today() - timedelta(days=7)

    for g in grouped:
        produit = g["produit_nom"]
        # Variation 7 jours
        prix_actuel_qs = (
            PrixMarche.objects
            .filter(produit_nom=produit, date_relevee__gte=date.today() - timedelta(days=3))
            .aggregate(moy=Avg("prix_unitaire"))
        )
        prix_ref_qs = (
            PrixMarche.objects
            .filter(
                produit_nom=produit,
                date_relevee__gte=date_ref - timedelta(days=3),
                date_relevee__lte=date_ref + timedelta(days=3),
            )
            .aggregate(moy=Avg("prix_unitaire"))
        )
        prix_actuel = prix_actuel_qs["moy"]
        prix_ref    = prix_ref_qs["moy"]

        variation_7j = None
        if prix_actuel and prix_ref and float(prix_ref) > 0:
            variation_7j = round((float(prix_actuel) - float(prix_ref)) / float(prix_ref) * 100, 1)

        # Alerte associée (la plus récente et la plus grave)
        alerte = (
            AlertePrix.objects
            .filter(produit_nom=produit, periode_jours=7)
            .order_by("-date_detection")
            .first()
        )

        result.append({
            "produit_nom":   produit,
            "prix_moyen":    round(float(g["prix_moyen"]), 0) if g["prix_moyen"] else None,
            "prix_min":      round(float(g["prix_min"]), 0)   if g["prix_min"] else None,
            "prix_max":      round(float(g["prix_max"]), 0)   if g["prix_max"] else None,
            "variation_7j":  variation_7j,
            "alerte_niveau": alerte.niveau if alerte else None,
        })

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PAGES PUBLIQUES SEO — prix du marché (data-driven : jamais de page vide)
# ─────────────────────────────────────────────────────────────────────────────

# Fenêtre « données récentes » : au-delà, on considère qu'il n'y a pas de prix.
RECENT_JOURS = 90

# Produits exposés publiquement : slug propre (URL), libellé, article français
# correct (« du mil », « de l'oignon ») et termes de matching sur produit_nom (libre).
PRODUITS_PUBLICS = [
    {"slug": "mil",      "label": "Mil",      "det_de": "du mil",        "termes": ["mil"]},
    {"slug": "sorgho",   "label": "Sorgho",   "det_de": "du sorgho",     "termes": ["sorgho"]},
    {"slug": "mais",     "label": "Maïs",     "det_de": "du maïs",       "termes": ["maïs", "mais"]},
    {"slug": "riz",      "label": "Riz",      "det_de": "du riz",        "termes": ["riz"]},
    {"slug": "arachide", "label": "Arachide", "det_de": "de l'arachide", "termes": ["arachide"]},
    {"slug": "niebe",    "label": "Niébé",    "det_de": "du niébé",      "termes": ["niébé", "niebe"]},
    {"slug": "oignon",   "label": "Oignon",   "det_de": "de l'oignon",   "termes": ["oignon"]},
    {"slug": "tomate",   "label": "Tomate",   "det_de": "de la tomate",  "termes": ["tomate"]},
]
_PRODUITS_PUBLICS_BY_SLUG = {p["slug"]: p for p in PRODUITS_PUBLICS}


def _q_produit(termes: list[str]) -> Q:
    """Filtre OR sur produit_nom (le champ est du texte libre normalisé)."""
    q = Q()
    for t in termes:
        q |= Q(produit_nom__icontains=t)
    return q


@require_GET
def prix_public_liste(request):
    """Page pilier publique : produits AYANT des données récentes uniquement."""
    cutoff = date.today() - timedelta(days=RECENT_JOURS)
    produits = []
    for p in PRODUITS_PUBLICS:
        agg = (
            PrixMarche.objects
            .filter(_q_produit(p["termes"]), date_relevee__gte=cutoff)
            .aggregate(moy=Avg("prix_unitaire"), n=Count("id"), dmax=Max("date_relevee"))
        )
        if agg["n"]:
            produits.append({
                "slug": p["slug"], "label": p["label"],
                "prix_moyen": round(float(agg["moy"]), 0) if agg["moy"] else None,
                "date": agg["dmax"], "nb": agg["n"],
            })
    return render(request, "marche/public_liste.html", {
        "produits": produits,
        "vide": not produits,            # → le template pose noindex (anti thin-content)
        "seo_title": "Prix des produits agricoles au Sénégal | Andd Baay",
        "seo_description": (
            "Prix du marché des produits agricoles au Sénégal (mil, riz, arachide, "
            "oignon, tomate…) : moyennes par marché, sources FAO/OMA, mises à jour régulières."
        ),
        "page_h1": "Prix des produits agricoles au Sénégal",
        "intro_text": (
            "Suivez les prix observés sur les marchés sénégalais, agrégés depuis des "
            "sources officielles (FAO FPMA, OMA Sénégal)."
        ),
    })


@require_GET
def prix_public_detail(request, slug):
    """Fiche prix par produit. 404 si slug inconnu OU pas de données récentes."""
    p = _PRODUITS_PUBLICS_BY_SLUG.get(slug)
    if p is None:
        raise Http404("Produit inconnu.")

    cutoff = date.today() - timedelta(days=RECENT_JOURS)
    base_qs = PrixMarche.objects.filter(_q_produit(p["termes"]), date_relevee__gte=cutoff)
    agg = base_qs.aggregate(
        moy=Avg("prix_unitaire"), pmin=Min("prix_unitaire"),
        pmax=Max("prix_unitaire"), n=Count("id"), dmax=Max("date_relevee"),
    )
    if not agg["n"]:
        raise Http404("Pas de données de prix récentes pour ce produit.")

    # Dernier relevé par marché (le plus récent par marché).
    par_marche: dict[str, dict] = {}
    for r in base_qs.order_by("marche_nom", "-date_relevee").values(
        "marche_nom", "region", "prix_unitaire", "unite", "date_relevee", "source"
    ):
        par_marche.setdefault(r["marche_nom"], r)
    lignes = sorted(par_marche.values(), key=lambda r: r["marche_nom"])
    unite = lignes[0]["unite"] if lignes else "FCFA/kg"
    det_de = p["det_de"]

    return render(request, "marche/public_detail.html", {
        "produit": p,
        "lignes": lignes,
        "prix_moyen": round(float(agg["moy"]), 0) if agg["moy"] else None,
        "prix_min": round(float(agg["pmin"]), 0) if agg["pmin"] else None,
        "prix_max": round(float(agg["pmax"]), 0) if agg["pmax"] else None,
        "unite": unite,
        "date_maj": agg["dmax"],
        "nb": agg["n"],
        "seo_title": f"Prix {det_de} au Sénégal — marchés & tendances | Andd Baay",
        "seo_description": (
            f"Prix {det_de} sur les marchés du Sénégal : moyenne, minimum et maximum "
            f"par marché. Données FAO/OMA, dernière mise à jour {agg['dmax']:%d/%m/%Y}."
        ),
        "page_h1": f"Prix {det_de} au Sénégal",
    })


# ─────────────────────────────────────────────────────────────────────────────
# HTMX — marquer une alerte comme vue
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def marquer_alerte_vue(request, pk):
    """POST /marche/prix/alertes/<pk>/vue/ — marque l'alerte vue, retourne 204."""
    alerte = get_object_or_404(AlertePrix, pk=pk)
    alerte.vue = True
    alerte.save(update_fields=["vue"])
    return JsonResponse({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Données JSON pour les graphiques Chart.js
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_GET
def graphique_prix_json(request):
    """
    GET /marche/prix/graphique/?produit=mil&marche=Kaolack&periode=30

    Retourne les données Chart.js pour un graphique de ligne :
    {
      "labels": ["2025-01-01", ...],
      "datasets": [{"label": "Kaolack", "data": [250, 260, ...]}]
    }
    """
    produit = request.GET.get("produit", "").strip()
    marche  = request.GET.get("marche", "").strip()
    try:
        periode = int(request.GET.get("periode", 30))
        periode = max(7, min(90, periode))
    except (ValueError, TypeError):
        periode = 30

    if not produit:
        return JsonResponse({"labels": [], "datasets": []})

    date_debut = date.today() - timedelta(days=periode)

    qs = PrixMarche.objects.filter(
        produit_nom__icontains=produit,
        date_relevee__gte=date_debut,
    ).order_by("date_relevee")

    if marche:
        qs = qs.filter(marche_nom__icontains=marche)

    # Grouper par marché
    marches: dict[str, dict[str, float]] = {}
    for p in qs.values("marche_nom", "date_relevee", "prix_unitaire"):
        m = p["marche_nom"]
        d = str(p["date_relevee"])
        if m not in marches:
            marches[m] = {}
        # Moyenne si plusieurs entrées pour le même jour
        existing = marches[m].get(d)
        if existing is None:
            marches[m][d] = float(p["prix_unitaire"])
        else:
            marches[m][d] = (existing + float(p["prix_unitaire"])) / 2

    if not marches:
        return JsonResponse({"labels": [], "datasets": []})

    # Union de toutes les dates
    all_dates = sorted({d for dates in marches.values() for d in dates.keys()})

    # Couleurs distinctes
    _COLORS = [
        "#1D9E75", "#0369a1", "#b45309", "#7c3aed",
        "#dc2626", "#0891b2", "#65a30d", "#d97706",
    ]

    datasets = []
    for i, (marche_nom, date_prix) in enumerate(marches.items()):
        color = _COLORS[i % len(_COLORS)]
        datasets.append({
            "label":           marche_nom,
            "data":            [date_prix.get(d) for d in all_dates],
            "borderColor":     color,
            "backgroundColor": color + "22",
            "borderWidth":     2,
            "tension":         0.3,
            "spanGaps":        True,
            "pointRadius":     3,
        })

    return JsonResponse({
        "labels":   all_dates,
        "datasets": datasets,
        "produit":  produit,
        "periode":  periode,
    })
