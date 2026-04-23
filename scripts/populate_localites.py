import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Andd_Baayi.settings')
django.setup()

from baay.models import Localite

localites_sn = [
    {"nom": "Dakar", "latitude": 14.7167, "longitude": -17.4677},
    {"nom": "Diourbel", "latitude": 14.65, "longitude": -16.2333},
    {"nom": "Fatick", "latitude": 14.3581, "longitude": -16.4056},
    {"nom": "Kaffrine", "latitude": 14.1059, "longitude": -15.5508},
    {"nom": "Kaolack", "latitude": 14.1333, "longitude": -16.25},
    {"nom": "Kédougou", "latitude": 12.55, "longitude": -12.1833},
    {"nom": "Kolda", "latitude": 12.8833, "longitude": -14.95},
    {"nom": "Louga", "latitude": 15.6167, "longitude": -16.2333},
    {"nom": "Matam", "latitude": 15.65, "longitude": -13.25},
    {"nom": "Saint-Louis", "latitude": 16.0333, "longitude": -16.4833},
    {"nom": "Sédhiou", "latitude": 12.7081, "longitude": -15.5539},
    {"nom": "Tambacounda", "latitude": 13.7667, "longitude": -13.6667},
    {"nom": "Thiès", "latitude": 14.8333, "longitude": -16.9333},
    {"nom": "Ziguinchor", "latitude": 12.5833, "longitude": -16.2667},
    # Major agricultural zones
    {"nom": "Richard-Toll", "latitude": 16.4333, "longitude": -15.7},
    {"nom": "Podor", "latitude": 16.65, "longitude": -14.95},
    {"nom": "Ross Bétio", "latitude": 16.2667, "longitude": -16.1833},
    {"nom": "Nioro du Rip", "latitude": 13.7333, "longitude": -15.7667},
    {"nom": "Bignona", "latitude": 12.8167, "longitude": -16.2333},
    {"nom": "Vélingara", "latitude": 13.15, "longitude": -14.1167},
    {"nom": "Dagana", "latitude": 16.4167, "longitude": -15.6},
    {"nom": "Tivaouane", "latitude": 14.95, "longitude": -16.8167},
    {"nom": "Niakhar", "latitude": 14.3333, "longitude": -16.4},
    {"nom": "Bambey", "latitude": 14.6833, "longitude": -16.45},
    {"nom": "Guinguinéo", "latitude": 14.2667, "longitude": -15.95},
    {"nom": "Mbour", "latitude": 14.4167, "longitude": -16.9667},
    {"nom": "Rufisque", "latitude": 14.7167, "longitude": -17.2667},
]

for loc in localites_sn:
    obj, created = Localite.objects.get_or_create(
        nom=loc['nom'],
        defaults={
            'latitude': loc['latitude'],
            'longitude': loc['longitude'],
            'type_sol': 'Non spécifié',
            'conditions_meteo': 'Typique de la région',
        }
    )
    if not created:
        obj.latitude = loc['latitude']
        obj.longitude = loc['longitude']
        obj.save()

print(f"{len(localites_sn)} localités vérifiées/ajoutées avec succès.")
