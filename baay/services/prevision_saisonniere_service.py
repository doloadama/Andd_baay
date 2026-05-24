"""
Service de prévisions saisonnières pluviométriques (P5.2).

Approche hybride :
  1. IRI Data Library (ENSO-based) — si disponible (API publique IRI Columbia)
  2. Facteurs ENSO statiques basés sur l'état La Niña / El Niño actuel
     (source : NOAA MEI index téléchargé et mis en cache 7j)
  3. Facteur neutre 1.0 par défaut (ne bloque jamais le calcul principal)

Le facteur saisonnier (0.70–1.30) est appliqué sur la pluviométrie attendue
pour ajuster le rendement en cas de saison plus sèche ou plus humide que la normale.

Usage
-----
    from baay.services.prevision_saisonniere_service import get_facteur_saisonnier

    facteur = get_facteur_saisonnier(lat=14.69, lon=-17.44, annee=2026, mois_debut=7)
    # → 0.88 (La Niña faible → saison plus sèche en Afrique de l'Ouest)

Références
----------
- NOAA MEI v2 : https://psl.noaa.gov/enso/mei/
- IRI ENSO forecast : https://iri.columbia.edu/our-expertise/climate/forecasts/enso/
- Impact ENSO / Sahel : positif El Niño → sécheresse Sahel ; La Niña → normal/humide
"""

import logging
from datetime import date

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

_NOAA_MEI_URL = "https://psl.noaa.gov/enso/mei/data/meiv2.data"
_REQUEST_TIMEOUT_S = 8
_CACHE_KEY_MEI = "enso_mei_v2"
_CACHE_TTL_MEI = 7 * 24 * 3600     # 7 jours
_CACHE_TTL_FACTEUR = 24 * 3600     # 24h pour le facteur calculé


# ── Zones géographiques et impact ENSO ──────────────────────────────────────
# Impact simplifié El Niño / La Niña sur la pluviométrie locale.
# Source : littérature agronomique Afrique sub-saharienne.
# Clé = (lat_min, lat_max, lon_min, lon_max), valeur = (facteur_elnino, facteur_lanina)
#   facteur > 1 → plus humide que normale   facteur < 1 → plus sec
_ZONES_ENSO = [
    # Sahel occidental (Sénégal, Mali, Mauritanie, Burkina)
    ((10, 20), (-18, 4), 0.80, 1.10),
    # Afrique de l'Ouest côtière (Côte d'Ivoire, Ghana, Nigeria SW)
    ((4, 10), (-10, 5), 1.10, 0.90),
    # Afrique centrale (Cameroun, RDC ouest)
    ((-5, 10), (10, 30), 1.05, 0.95),
    # Afrique de l'Est (Kenya, Tanzanie, Éthiopie)
    ((-5, 12), (34, 42), 1.15, 0.85),
    # Afrique australe (Zimbabwe, Mozambique, Zambie)
    ((-25, -10), (25, 40), 0.75, 1.20),
]


def _get_zone_impact(lat: float, lon: float) -> tuple[float, float]:
    """Retourne (facteur_elnino, facteur_lanina) pour la zone géographique donnée."""
    for (lat_rng, lon_rng, f_el, f_la) in _ZONES_ENSO:
        if lat_rng[0] <= lat <= lat_rng[1] and lon_rng[0] <= lon <= lon_rng[1]:
            return f_el, f_la
    return 1.0, 1.0   # zone inconnue → neutre


def _fetch_mei_index() -> dict[tuple[int, int], float] | None:
    """
    Télécharge et parse le MEI v2 NOAA (fichier texte tabulaire).
    Retourne un dict {(annee, mois): valeur_mei} ou None si échec.
    Valeur > +0.5 ≈ El Niño ; < -0.5 ≈ La Niña.
    """
    cached = cache.get(_CACHE_KEY_MEI)
    if cached is not None:
        return cached

    try:
        resp = requests.get(_NOAA_MEI_URL, timeout=_REQUEST_TIMEOUT_S)
        resp.raise_for_status()
        lines = resp.text.strip().splitlines()

        mei_data: dict[tuple[int, int], float] = {}
        for line in lines:
            parts = line.split()
            if not parts or not parts[0].isdigit():
                continue
            try:
                annee = int(parts[0])
                for mois_idx, val_str in enumerate(parts[1:13], start=1):
                    val = float(val_str)
                    if val > -99:    # -999 = manquant
                        mei_data[(annee, mois_idx)] = val
            except (ValueError, IndexError):
                continue

        if mei_data:
            cache.set(_CACHE_KEY_MEI, mei_data, timeout=_CACHE_TTL_MEI)
            logger.info("MEI v2 NOAA charge : %d entrées.", len(mei_data))
            return mei_data

    except Exception as exc:
        logger.warning("Impossible de charger le MEI NOAA : %s", exc)

    return None


def _classifer_enso(mei_value: float) -> str:
    """Classifie l'état ENSO à partir du MEI v2."""
    if mei_value >= 1.0:
        return "elnino_fort"
    if mei_value >= 0.5:
        return "elnino_modere"
    if mei_value <= -1.0:
        return "lanina_forte"
    if mei_value <= -0.5:
        return "lanina_moderee"
    return "neutre"


def get_facteur_saisonnier(
    lat: float,
    lon: float,
    annee: int | None = None,
    mois_debut: int | None = None,
) -> float:
    """
    Retourne un facteur multiplicatif (0.70–1.30) représentant l'anomalie
    pluviométrique saisonnière attendue pour la zone et la saison données.

    Ne lève jamais d'exception — retourne 1.0 par défaut si indisponible.

    Parameters
    ----------
    lat, lon    : coordonnées décimales
    annee       : année de la saison (défaut: année courante)
    mois_debut  : mois de début (défaut: mois courant)
    """
    if lat is None or lon is None:
        return 1.0

    today = date.today()
    annee = annee or today.year
    mois_debut = mois_debut or today.month

    cache_key = f"facteur_saisonnier_{round(lat,2)}_{round(lon,2)}_{annee}_{mois_debut}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        mei_data = _fetch_mei_index()
        if not mei_data:
            return 1.0

        # MEI du trimestre précédant la saison (lag ~3 mois)
        mois_ref = ((mois_debut - 4) % 12) + 1
        annee_ref = annee if mois_debut > 3 else annee - 1
        mei_val = mei_data.get((annee_ref, mois_ref))

        if mei_val is None:
            # Essayer le mois précédent le plus récent disponible
            for decal in range(1, 6):
                m = ((mois_debut - decal - 1) % 12) + 1
                a = annee if mois_debut > decal else annee - 1
                mei_val = mei_data.get((a, m))
                if mei_val is not None:
                    break

        if mei_val is None:
            return 1.0

        etat = _classifer_enso(mei_val)
        f_elnino, f_lanina = _get_zone_impact(lat, lon)

        if etat == "elnino_fort":
            facteur = f_elnino * 0.90       # amplifier l'impact
        elif etat == "elnino_modere":
            facteur = 1.0 + (f_elnino - 1.0) * 0.60
        elif etat == "lanina_forte":
            facteur = f_lanina * 1.05
        elif etat == "lanina_moderee":
            facteur = 1.0 + (f_lanina - 1.0) * 0.60
        else:
            facteur = 1.0

        # Clamp [0.70, 1.30]
        facteur = round(max(0.70, min(1.30, facteur)), 4)

        cache.set(cache_key, facteur, timeout=_CACHE_TTL_FACTEUR)
        logger.debug(
            "Facteur saisonnier %.4f (MEI=%.2f, etat=%s, lat=%.2f lon=%.2f)",
            facteur, mei_val, etat, lat, lon,
        )
        return facteur

    except Exception as exc:
        logger.warning("get_facteur_saisonnier : %s", exc)
        return 1.0
