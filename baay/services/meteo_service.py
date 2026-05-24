"""
Service de pluviométrie réelle via l'API Open-Meteo Historical Archive.

Open-Meteo est gratuit, sans clé d'API, et fournit des données ERA5/CERRA
à résolution ~10 km² pour toutes les coordonnées mondiales.
Endpoint : https://archive-api.open-meteo.com/v1/archive

Usage typique
-------------
    from baay.services.meteo_service import fetch_precipitation_depuis_semis

    pluie_mm = fetch_precipitation_depuis_semis(14.69, -17.44, date(2025, 7, 15))
    # → 412.3  (cumul mm entre la date de semis et aujourd'hui)

Comportement en cas d'échec
----------------------------
    - Toujours retourne None (ne bloque jamais estimer_rendement_ia)
    - Erreurs loguées en WARNING (pas en ERROR)
    - Cache Redis 6h par (lat, lon, date_semis) pour éviter les appels répétés
"""

import logging
from datetime import date, timedelta

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

_OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
_REQUEST_TIMEOUT_S = 6         # timeout HTTP strict
_CACHE_TTL_S = 6 * 3600        # 6 heures
_MAX_HISTORY_DAYS = 548        # 18 mois max (au-delà les données ERA5 sont fiables)


def _cache_key(lat: float, lon: float, date_semis: date) -> str:
    lat_r = round(lat, 3)
    lon_r = round(lon, 3)
    return f"meteo_pluie_{lat_r}_{lon_r}_{date_semis.isoformat()}"


def fetch_precipitation_depuis_semis(
    lat: float,
    lon: float,
    date_semis: date,
) -> float | None:
    """
    Retourne le cumul de précipitations (en mm) entre `date_semis` et hier.

    Parameters
    ----------
    lat, lon    : coordonnées décimales de la parcelle / localité
    date_semis  : date de début (inclusive)

    Returns
    -------
    float (mm) ou None si données indisponibles, hors délai, ou erreur HTTP.
    """
    if lat is None or lon is None or date_semis is None:
        return None

    today = date.today()
    date_fin = today - timedelta(days=1)   # hier (données du jour non encore consolidées)

    if date_semis > date_fin:
        # Semis futur ou d'hier → pas encore de données
        return None

    # Limiter l'horizon pour éviter les requêtes trop longues
    date_debut_effective = max(date_semis, today - timedelta(days=_MAX_HISTORY_DAYS))
    if date_debut_effective > date_fin:
        return None

    key = _cache_key(lat, lon, date_semis)
    cached = cache.get(key)
    if cached is not None:
        return cached

    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start_date": date_debut_effective.isoformat(),
        "end_date": date_fin.isoformat(),
        "daily": "precipitation_sum",
        "timezone": "UTC",
    }

    try:
        resp = requests.get(
            _OPEN_METEO_ARCHIVE_URL,
            params=params,
            timeout=_REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()

        daily = data.get("daily", {})
        valeurs = daily.get("precipitation_sum", [])
        # Somme en ignorant les None (jours sans données)
        cumul = sum(v for v in valeurs if v is not None)
        cumul = round(cumul, 1)

        cache.set(key, cumul, timeout=_CACHE_TTL_S)
        logger.debug(
            "Open-Meteo : %.1f mm (lat=%.3f lon=%.3f depuis %s)",
            cumul, lat, lon, date_debut_effective,
        )
        return cumul

    except requests.exceptions.Timeout:
        logger.warning("Open-Meteo : timeout (lat=%.3f lon=%.3f)", lat, lon)
    except requests.exceptions.RequestException as exc:
        logger.warning("Open-Meteo : erreur HTTP : %s", exc)
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Open-Meteo : réponse inattendue : %s", exc)

    return None


def fetch_precipitation_annuelle_moyenne(
    lat: float,
    lon: float,
    annees: int = 5,
) -> float | None:
    """
    Retourne la pluviométrie annuelle moyenne (mm/an) sur les `annees` dernières
    années complètes, comme alternative à Localite.pluviometrie_moyenne.

    Utile quand la localite n'a pas de pluviometrie_moyenne renseignée.
    """
    if lat is None or lon is None:
        return None

    today = date.today()
    date_fin = date(today.year - 1, 12, 31)
    date_debut = date(today.year - annees, 1, 1)

    key = f"meteo_pluie_annuelle_{round(lat,3)}_{round(lon,3)}_{annees}ans"
    cached = cache.get(key)
    if cached is not None:
        return cached

    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start_date": date_debut.isoformat(),
        "end_date": date_fin.isoformat(),
        "daily": "precipitation_sum",
        "timezone": "UTC",
    }

    try:
        resp = requests.get(
            _OPEN_METEO_ARCHIVE_URL,
            params=params,
            timeout=_REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()

        valeurs = data.get("daily", {}).get("precipitation_sum", [])
        total = sum(v for v in valeurs if v is not None)
        moyenne = round(total / annees, 1) if annees > 0 else None

        cache.set(key, moyenne, timeout=24 * 3600)
        logger.debug(
            "Open-Meteo moy. annuelle : %.1f mm/an (%.3f, %.3f, %d ans)",
            moyenne, lat, lon, annees,
        )
        return moyenne

    except Exception as exc:
        logger.warning("Open-Meteo moy. annuelle : %s", exc)
        return None
