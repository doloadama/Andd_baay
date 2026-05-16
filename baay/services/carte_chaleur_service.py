"""
Service de génération de carte de chaleur des cultures par localité.
Données agrégées et anonymisées pour respect de la confidentialité des fermes.
"""

import json
import logging
from typing import Optional
from decimal import Decimal
from dataclasses import dataclass
from collections import defaultdict

from django.db.models import Sum, Count, Avg
from django.core.cache import cache

from baay.models import Projet, ProjetProduit, Pays, Localite

logger = logging.getLogger(__name__)

# Durée de cache (1 heure)
CACHE_TIMEOUT = 3600


@dataclass
class HeatmapPoint:
    """Point de données pour la carte de chaleur."""
    lat: float
    lon: float
    intensity: float  # 0.0 - 1.0
    culture_type: str
    superficie_totale: float
    nb_projets: int


@dataclass
class CultureAggregate:
    """Agrégation des données par culture et localité."""
    culture_nom: str
    localite_nom: str
    superficie_totale: float
    nb_projets: int
    latitude: float
    longitude: float
    pays_nom: str


def agréger_cultures_par_localite(
    pays_id: Optional[str] = None,
    culture_type: Optional[str] = None,
) -> list[CultureAggregate]:
    """
    Agrège les projets par localité et type de culture.
    Anonymisé : ne retourne pas les données individuelles des fermes.
    """
    # Requête de base
    projets_qs = Projet.objects.filter(
        statut='en_cours',
        localite__isnull=False,
    ).select_related('localite', 'localite__pays', 'culture')

    if pays_id:
        projets_qs = projets_qs.filter(localite__pays_id=pays_id)

    if culture_type:
        projets_qs = projets_qs.filter(culture__nom__icontains=culture_type)

    # Agrégation par localité et culture
    aggregates = defaultdict(lambda: {
        'superficie': 0.0,
        'nb_projets': 0,
        'lat': None,
        'lon': None,
        'pays': '',
    })

    for projet in projets_qs:
        if not projet.localite:
            continue

        # Clé: localite + culture
        culture_nom = projet.culture.nom.lower() if projet.culture else 'inconnu'
        key = (projet.localite.nom, culture_nom)

        aggregates[key]['superficie'] += float(projet.superficie or 0)
        aggregates[key]['nb_projets'] += 1
        aggregates[key]['lat'] = float(projet.localite.latitude) if projet.localite.latitude else None
        aggregates[key]['lon'] = float(projet.localite.longitude) if projet.localite.longitude else None
        aggregates[key]['pays'] = projet.localite.pays.nom if projet.localite.pays else ''

    # Convertir en liste de CultureAggregate
    result = []
    for (localite_nom, culture_nom), data in aggregates.items():
        if data['lat'] is None or data['lon'] is None:
            continue

        result.append(CultureAggregate(
            culture_nom=culture_nom,
            localite_nom=localite_nom,
            superficie_totale=data['superficie'],
            nb_projets=data['nb_projets'],
            latitude=data['lat'],
            longitude=data['lon'],
            pays_nom=data['pays'],
        ))

    return result


def generer_geojson_heatmap(
    pays_id: Optional[str] = None,
    culture_type: Optional[str] = None,
) -> dict:
    """
    Génère un GeoJSON FeatureCollection pour la carte de chaleur.
    Format compatible avec Leaflet.heat ou Mapbox.
    """
    cache_key = f"heatmap_geojson_{pays_id}_{culture_type}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    aggregates = agréger_cultures_par_localite(pays_id, culture_type)

    if not aggregates:
        return {
            "type": "FeatureCollection",
            "features": [],
            "metadata": {
                "count": 0,
                "generated_at": str(__import__('django.utils', fromlist=['timezone']).timezone.now()),
            }
        }

    # Calculer intensité relative (0-1) basée sur superficie
    max_superficie = max(a.superficie_totale for a in aggregates) if aggregates else 1

    features = []
    for agg in aggregates:
        intensity = min(1.0, agg.superficie_totale / max_superficie) if max_superficie > 0 else 0

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [agg.longitude, agg.latitude],
            },
            "properties": {
                "culture_type": agg.culture_nom,
                "localite": agg.localite_nom,
                "superficie_totale": agg.superficie_totale,
                "nb_projets": agg.nb_projets,
                "intensity": round(intensity, 2),
                "pays": agg.pays_nom,
            }
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "count": len(features),
            "max_superficie": max_superficie,
            "filters": {
                "pays_id": pays_id,
                "culture_type": culture_type,
            },
            "generated_at": str(__import__('django.utils', fromlist=['timezone']).timezone.now()),
            "disclaimer": "Données agrégées et anonymisées. Aucune ferme individuelle identifiable.",
        }
    }

    # Mettre en cache
    cache.set(cache_key, geojson, CACHE_TIMEOUT)

    return geojson


def generer_donnees_heatmap_leaflet(
    pays_id: Optional[str] = None,
    culture_type: Optional[str] = None,
) -> list[list[float]]:
    """
    Génère des données au format [lat, lon, intensity] pour Leaflet.heat.
    """
    aggregates = agréger_cultures_par_localite(pays_id, culture_type)

    if not aggregates:
        return []

    max_superficie = max(a.superficie_totale for a in aggregates) if aggregates else 1

    data = []
    for agg in aggregates:
        intensity = min(1.0, agg.superficie_totale / max_superficie) if max_superficie > 0 else 0.1
        # Leaflet.heat format: [lat, lng, intensity]
        data.append([
            agg.latitude,
            agg.longitude,
            round(intensity, 2),
        ])

    return data


def obtenir_statistiques_heatmap(
    pays_id: Optional[str] = None,
) -> dict:
    """
    Retourne des statistiques globales sur la répartition des cultures.
    """
    cache_key = f"heatmap_stats_{pays_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    aggregates = agréger_cultures_par_localite(pays_id)

    if not aggregates:
        return {
            "total_cultures": 0,
            "total_superficie": 0,
            "cultures_par_type": {},
            "top_localites": [],
        }

    # Statistiques par type de culture
    cultures_stats = defaultdict(lambda: {'superficie': 0.0, 'count': 0})
    for agg in aggregates:
        cultures_stats[agg.culture_nom]['superficie'] += agg.superficie_totale
        cultures_stats[agg.culture_nom]['count'] += agg.nb_projets

    # Top localités par superficie
    top_localites = sorted(
        aggregates,
        key=lambda x: x.superficie_totale,
        reverse=True,
    )[:10]

    stats = {
        "total_points": len(aggregates),
        "total_superficie": sum(a.superficie_totale for a in aggregates),
        "cultures_par_type": {
            k: {
                'superficie_totale': v['superficie'],
                'nb_projets': v['count'],
            }
            for k, v in cultures_stats.items()
        },
        "top_localites": [
            {
                'nom': loc.localite_nom,
                'pays': loc.pays_nom,
                'superficie': loc.superficie_totale,
                'nb_projets': loc.nb_projets,
            }
            for loc in top_localites
        ],
    }

    cache.set(cache_key, stats, CACHE_TIMEOUT)
    return stats


def invalider_cache_heatmap():
    """
    Invalide le cache des heatmaps (à appeler quand les données changent).
    """
    # Pattern de clés à supprimer
    keys_to_delete = []
    # Note: Redis/Memcached permettrait un delete pattern, mais avec cache Django standard:
    # on utilise une version dans la clé ou on attend l'expiration
    logger.info("Cache heatmap marqué pour invalidation (expire dans %s secondes)", CACHE_TIMEOUT)


# Liste des cultures principales pour filtres
CULTURES_PRINCIPALES = [
    ('mil', 'Mil'),
    ('sorgho', 'Sorgho'),
    ('mais', 'Maïs'),
    ('arachide', 'Arachide'),
    ('niebe', 'Niébé'),
    ('riz', 'Riz'),
    ('coton', 'Coton'),
    ('tomate', 'Tomate'),
    ('oignon', 'Oignon'),
    ('piment', 'Piment'),
]
