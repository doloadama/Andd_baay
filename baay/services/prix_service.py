# baay/services/prix_service.py
"""
Service de collecte et d'analyse des prix agricoles au Sénégal.

Sources :
  1. FAO FPMA API  — https://fpma.fao.org/giews/fpma/  (primaire, sans clé, JSON)
  2. OMA Sénégal   — http://www.oma.gouv.sn/            (fallback, scraping HTML)

Exports principaux
──────────────────
  fetch_prix_fao_fpma(pays="SEN")        → (nb_crees, nb_mis_a_jour)
  fetch_prix_oma()                       → (nb_crees, nb_mis_a_jour)
  detecter_variations_significatives(…)  → list[AlertePrix créées]
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from django.core.cache import cache
from django.db import transaction
from django.utils.timezone import now

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT   = 10          # secondes
_CACHE_TTL_12H  = 43_200      # 12 heures en secondes
_CACHE_KEY_FAO  = "prix_fao_fpma_SEN"

# ── Seuils de variation ───────────────────────────────────────────────────────
SEUIL_WARNING_7J   = 15.0   # % sur 7 jours
SEUIL_CRITIQUE_7J  = 30.0   # % sur 7 jours
SEUIL_WARNING_30J  = 20.0   # % sur 30 jours
SEUIL_CRITIQUE_30J = 40.0   # % sur 30 jours

# ── Mapping noms FAO → noms normalisés ───────────────────────────────────────
_FAO_PRODUIT_MAP: dict[str, str] = {
    "Millet":             "mil",
    "Sorghum":            "sorgho",
    "Maize":              "maïs",
    "Maize (white)":      "maïs",
    "Rice":               "riz",
    "Rice (local)":       "riz local",
    "Rice (imported)":    "riz importé",
    "Groundnuts":         "arachide",
    "Groundnut oil":      "huile d'arachide",
    "Cowpeas":            "niébé",
    "Beans":              "niébé",
    "Onion":              "oignon",
    "Tomatoes":           "tomate",
    "Sweet potatoes":     "patate douce",
    "Cassava":            "manioc",
    "Wheat":              "blé",
    "Sugar":              "sucre",
    "Salt":               "sel",
    "Palm oil":           "huile de palme",
}

# Fallback : mots-clés pour normalisation partielle
_FAO_KEYWORDS: list[tuple[str, str]] = [
    ("millet",       "mil"),
    ("sorghum",      "sorgho"),
    ("maize",        "maïs"),
    ("corn",         "maïs"),
    ("rice",         "riz"),
    ("groundnut",    "arachide"),
    ("peanut",       "arachide"),
    ("cowpea",       "niébé"),
    ("bean",         "niébé"),
    ("onion",        "oignon"),
    ("tomato",       "tomate"),
    ("sweet potato", "patate douce"),
    ("cassava",      "manioc"),
    ("yam",          "igname"),
    ("wheat",        "blé"),
    ("sugar",        "sucre"),
    ("palm oil",     "huile de palme"),
]


def _normaliser_produit_fao(nom_fao: str) -> str:
    """Convertit un nom FAO anglais en nom normalisé français."""
    # Correspondance exacte d'abord
    if nom_fao in _FAO_PRODUIT_MAP:
        return _FAO_PRODUIT_MAP[nom_fao]
    # Mots-clés
    nom_lower = nom_fao.lower()
    for kw, nom in _FAO_KEYWORDS:
        if kw in nom_lower:
            return nom
    # Par défaut : on garde le nom FAO en minuscules
    return nom_fao.lower()


def _safe_decimal(val: Any) -> Decimal | None:
    """Convertit une valeur en Decimal, retourne None si impossible."""
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Source 1 : FAO FPMA API
# ─────────────────────────────────────────────────────────────────────────────

_FAO_FPMA_BASE = "https://fpma.fao.org/giews/fpma/rest"


def fetch_prix_fao_fpma(pays: str = "SEN") -> tuple[int, int]:
    """
    Collecte les prix depuis la FAO FPMA API pour le pays donné (ISO3).

    Retourne (nb_crees, nb_mis_a_jour).
    Met en cache le résultat brut 12 h pour éviter les appels répétés.
    """
    from baay.models import PrixMarche

    cached = cache.get(_CACHE_KEY_FAO)
    entries: list[dict] = []

    if cached is not None:
        entries = cached
        logger.debug("FAO FPMA : données depuis le cache Redis (%d entrées).", len(entries))
    else:
        entries = _fetch_fao_fpma_entries(pays)
        if entries:
            cache.set(_CACHE_KEY_FAO, entries, _CACHE_TTL_12H)

    nb_crees = nb_maj = 0

    with transaction.atomic():
        for entry in entries:
            prix = _safe_decimal(entry.get("price"))
            if prix is None or prix <= 0:
                continue

            date_str = entry.get("date") or entry.get("startDate", "")
            try:
                date_relevee = date.fromisoformat(date_str[:10])
            except (ValueError, TypeError):
                continue

            produit_fao = entry.get("commodity", {}).get("name", "") if isinstance(entry.get("commodity"), dict) else str(entry.get("commodity", ""))
            produit_nom = _normaliser_produit_fao(produit_fao)
            marche_nom  = entry.get("market", {}).get("name", "Marché Sénégal") if isinstance(entry.get("market"), dict) else str(entry.get("market", "Marché Sénégal"))
            region      = entry.get("market", {}).get("admin1", "") if isinstance(entry.get("market"), dict) else ""
            unite_raw   = entry.get("unit", {}).get("name", "kg") if isinstance(entry.get("unit"), dict) else str(entry.get("unit", "kg"))
            unite       = f"FCFA/{unite_raw}" if "FCFA" not in unite_raw and "XOF" not in unite_raw else unite_raw
            unite       = unite.replace("XOF", "FCFA")
            source_id   = str(entry.get("id", ""))
            qualite     = entry.get("type", {}).get("name", "") if isinstance(entry.get("type"), dict) else ""

            _, created = PrixMarche.objects.update_or_create(
                produit_nom=produit_nom,
                marche_nom=marche_nom,
                date_relevee=date_relevee,
                source=PrixMarche.SOURCE_FAO_FPMA,
                defaults={
                    "prix_unitaire": prix,
                    "unite":         unite[:30],
                    "region":        region[:100],
                    "qualite":       (qualite or "")[:50],
                    "source_id":     source_id[:200],
                },
            )
            if created:
                nb_crees += 1
            else:
                nb_maj += 1

    logger.info(
        "FAO FPMA [%s] : %d créés, %d mis à jour.",
        pays, nb_crees, nb_maj,
    )
    return nb_crees, nb_maj


def _fetch_fao_fpma_entries(pays: str) -> list[dict]:
    """Appel HTTP brut vers FAO FPMA. Retourne la liste d'entrées ou []."""
    # Endpoint v1 : données prix par pays
    url = f"{_FAO_FPMA_BASE}/data/CommodityPriceData"
    params = {
        "countryCode": pays,
        "page":        0,
        "pageSize":    500,
    }
    try:
        resp = requests.get(url, params=params, timeout=_HTTP_TIMEOUT, headers={"Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("FAO FPMA API indisponible : %s", exc)
        return []
    except ValueError as exc:
        logger.warning("FAO FPMA API : JSON invalide — %s", exc)
        return []

    # La réponse peut être une liste directe ou un dict avec 'data'
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("data", data.get("items", data.get("content", [])))
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Source 2 : OMA Sénégal (fallback scraping)
# ─────────────────────────────────────────────────────────────────────────────

_OMA_BASE_URL = "http://www.oma.gouv.sn"
_OMA_PRIX_URL = f"{_OMA_BASE_URL}/prix-des-produits.html"

# Produits connus par OMA (noms en français)
_OMA_PRODUITS_CONNUS: set[str] = {
    "mil", "sorgho", "maïs", "mais", "riz", "arachide", "niébé", "niebe",
    "oignon", "tomate", "patate douce", "manioc", "igname", "blé", "ble",
}


class PrixServiceUnavailable(Exception):
    """Levée quand aucune source de prix n'est disponible."""


def fetch_prix_oma() -> tuple[int, int]:
    """
    Collecte les prix depuis le site de l'OMA Sénégal (scraping HTML).

    Retourne (nb_crees, nb_mis_a_jour).
    Lève PrixServiceUnavailable si le site est inaccessible ou la structure HTML
    n'est pas reconnue (erreur propre, pas de crash de la tâche Celery).
    """
    from baay.models import PrixMarche

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("beautifulsoup4 non installé. Impossible de scraper l'OMA.")
        raise PrixServiceUnavailable("beautifulsoup4 manquant")

    try:
        resp = requests.get(_OMA_PRIX_URL, timeout=_HTTP_TIMEOUT, headers={
            "User-Agent": "Mozilla/5.0 (compatible; AnddBaay/1.0)",
        })
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("OMA Sénégal inaccessible : %s", exc)
        raise PrixServiceUnavailable(str(exc)) from exc

    try:
        soup = BeautifulSoup(resp.content, "html.parser")
        entries = _parse_oma_html(soup)
    except Exception as exc:
        logger.warning("OMA Sénégal : parsing HTML échoué — %s", exc)
        raise PrixServiceUnavailable(str(exc)) from exc

    if not entries:
        logger.warning("OMA Sénégal : aucune entrée parsée depuis %s", _OMA_PRIX_URL)
        raise PrixServiceUnavailable("Aucune entrée parsée")

    nb_crees = nb_maj = 0
    today = date.today()

    with transaction.atomic():
        for e in entries:
            prix = _safe_decimal(e.get("prix"))
            if prix is None or prix <= 0:
                continue
            _, created = PrixMarche.objects.update_or_create(
                produit_nom=e["produit"],
                marche_nom=e.get("marche", "Sénégal"),
                date_relevee=e.get("date", today),
                source=PrixMarche.SOURCE_OMA,
                defaults={
                    "prix_unitaire": prix,
                    "unite":         e.get("unite", "FCFA/kg")[:30],
                    "region":        e.get("region", "")[:100],
                    "qualite":       e.get("qualite", "")[:50],
                    "source_id":     "",
                },
            )
            if created:
                nb_crees += 1
            else:
                nb_maj += 1

    logger.info("OMA Sénégal : %d créés, %d mis à jour.", nb_crees, nb_maj)
    return nb_crees, nb_maj


def _parse_oma_html(soup) -> list[dict]:
    """
    Parse les tableaux de prix de l'OMA.

    L'OMA publie ses prix dans des tableaux HTML avec des colonnes variables.
    On recherche tous les <table> et <tr> contenant un produit reconnu.
    """
    results = []
    today = date.today()

    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]

        # Identifier les colonnes importantes
        col_produit = _find_col(headers, ["produit", "denrée", "denree", "article", "spécification"])
        col_prix    = _find_col(headers, ["prix", "price", "tarif", "cout", "coût"])
        col_marche  = _find_col(headers, ["marché", "marche", "place", "localité", "ville"])
        col_unite   = _find_col(headers, ["unité", "unite", "unit", "mesure"])
        col_date    = _find_col(headers, ["date", "période", "semaine"])

        if col_produit is None or col_prix is None:
            # Pas un tableau de prix reconnu
            continue

        for row in table.find_all("tr")[1:]:  # skip header
            cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if len(cells) <= max(filter(lambda x: x is not None, [col_produit, col_prix])):
                continue

            produit_raw = cells[col_produit] if col_produit < len(cells) else ""
            prix_raw    = cells[col_prix] if col_prix < len(cells) else ""
            marche_raw  = cells[col_marche] if col_marche is not None and col_marche < len(cells) else "Sénégal"
            unite_raw   = cells[col_unite] if col_unite is not None and col_unite < len(cells) else "kg"
            date_raw    = cells[col_date] if col_date is not None and col_date < len(cells) else ""

            produit = _normaliser_produit_oma(produit_raw)
            if not produit:
                continue

            # Nettoyer le prix
            prix_str = prix_raw.replace(" ", "").replace("\xa0", "").replace(",", ".").replace("FCFA", "").replace("XOF", "")
            try:
                prix = float(prix_str)
            except ValueError:
                continue

            # Unité
            unite = "FCFA/kg"
            if "sac" in unite_raw.lower() or "sac" in prix_raw.lower():
                unite = "FCFA/sac"
            elif "tonne" in unite_raw.lower():
                unite = "FCFA/tonne"

            # Date
            date_relevee = today
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    date_relevee = date.strptime(date_raw[:10], fmt)
                    break
                except (ValueError, TypeError):
                    pass

            results.append({
                "produit": produit,
                "prix":    prix,
                "marche":  marche_raw or "Sénégal",
                "unite":   unite,
                "date":    date_relevee,
                "region":  "",
                "qualite": "",
            })

    return results


def _find_col(headers: list[str], keywords: list[str]) -> int | None:
    """Retourne l'index de la première colonne correspondant à un mot-clé."""
    for kw in keywords:
        for i, h in enumerate(headers):
            if kw in h:
                return i
    return None


def _normaliser_produit_oma(raw: str) -> str:
    """Normalise un nom de produit brut OMA en nom standard."""
    clean = raw.lower().strip()
    # Correspondances directes
    direct = {
        "mil":          "mil",
        "sorgho":       "sorgho",
        "maïs":         "maïs",
        "mais":         "maïs",
        "riz":          "riz",
        "arachide":     "arachide",
        "niébé":        "niébé",
        "niebe":        "niébé",
        "haricot":      "niébé",
        "oignon":       "oignon",
        "tomate":       "tomate",
        "patate douce": "patate douce",
        "manioc":       "manioc",
        "igname":       "igname",
        "blé":          "blé",
        "ble":          "blé",
        "sucre":        "sucre",
        "sel":          "sel",
        "huile":        "huile",
    }
    for key, val in direct.items():
        if key in clean:
            return val
    return ""   # produit non reconnu → ignoré


# ─────────────────────────────────────────────────────────────────────────────
# Détection de variations (Task 6.4)
# ─────────────────────────────────────────────────────────────────────────────

def detecter_variations_significatives(
    periode_jours: int = 7,
    seuil_warning: float | None = None,
    seuil_critique: float | None = None,
) -> list:
    """
    Compare les prix récents aux prix N jours avant pour chaque (produit, marché).

    Crée des `AlertePrix` pour les variations dépassant les seuils.
    Idempotent : un seul `AlertePrix` par (produit, marché, période, jour de détection).

    Returns : liste des AlertePrix créées (pas mises à jour).
    """
    from baay.models import AlertePrix, PrixMarche
    from django.db.models import Avg

    # Seuils par défaut selon la période
    if seuil_warning is None:
        seuil_warning = SEUIL_WARNING_7J if periode_jours <= 7 else SEUIL_WARNING_30J
    if seuil_critique is None:
        seuil_critique = SEUIL_CRITIQUE_7J if periode_jours <= 7 else SEUIL_CRITIQUE_30J

    aujourd_hui  = date.today()
    date_ref     = aujourd_hui - timedelta(days=periode_jours)
    date_ref_min = date_ref - timedelta(days=3)   # tolérance ±3 jours

    # Prix récents (7 derniers jours)
    recents = (
        PrixMarche.objects
        .filter(date_relevee__gte=aujourd_hui - timedelta(days=7))
        .values("produit_nom", "marche_nom", "region", "unite")
        .annotate(prix_moyen=Avg("prix_unitaire"))
    )

    creees = []
    now_dt = now()

    for rec in recents:
        produit = rec["produit_nom"]
        marche  = rec["marche_nom"]
        unite   = rec["unite"]
        region  = rec["region"]
        prix_actuel = float(rec["prix_moyen"])

        # Prix de référence : moyenne sur la fenêtre autour de date_ref
        ref_qs = PrixMarche.objects.filter(
            produit_nom=produit,
            marche_nom=marche,
            date_relevee__gte=date_ref_min,
            date_relevee__lte=date_ref + timedelta(days=3),
        ).aggregate(prix_ref=Avg("prix_unitaire"))
        prix_ref = ref_qs["prix_ref"]

        if prix_ref is None or float(prix_ref) == 0:
            continue   # pas de données de référence

        variation_pct = (prix_actuel - float(prix_ref)) / float(prix_ref) * 100.0

        if abs(variation_pct) < seuil_warning:
            continue   # variation trop faible, pas d'alerte

        # Déterminer le niveau
        if abs(variation_pct) >= seuil_critique:
            niveau = AlertePrix.NIVEAU_CRITIQUE
        else:
            niveau = AlertePrix.NIVEAU_WARNING

        # Idempotence : 1 alerte max par (produit, marché, période, jour)
        # On utilise date_detection__date pour la contrainte quotidienne
        existe = AlertePrix.objects.filter(
            produit_nom=produit,
            marche_nom=marche,
            periode_jours=periode_jours,
            date_detection__date=aujourd_hui,
        ).exists()

        if existe:
            continue

        alerte = AlertePrix.objects.create(
            produit_nom=produit,
            marche_nom=marche,
            region=region,
            variation_pct=round(variation_pct, 2),
            prix_actuel=Decimal(str(round(prix_actuel, 2))),
            prix_reference=Decimal(str(round(float(prix_ref), 2))),
            unite=unite[:30],
            periode_jours=periode_jours,
            niveau=niveau,
        )
        creees.append(alerte)
        logger.info(
            "Alerte prix créée : %s %+.1f%% sur %dj [%s]",
            produit, variation_pct, periode_jours, niveau,
        )

    logger.info(
        "Détection variations (%dj) : %d alertes créées.",
        periode_jours, len(creees),
    )
    return creees
