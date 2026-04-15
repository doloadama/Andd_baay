import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Andd_Baayi.settings')
django.setup()

from baay.models import Pays, Localite

# Create Countries
pays_data = [
    {"nom": "Sénégal", "code_iso": "SN"},
    {"nom": "Mali", "code_iso": "ML"},
    {"nom": "Côte d'Ivoire", "code_iso": "CI"},
    {"nom": "Burkina Faso", "code_iso": "BF"},
    {"nom": "Guinée", "code_iso": "GN"},
]

pays_objs = {}
for p in pays_data:
    obj, _ = Pays.objects.get_or_create(nom=p["nom"], defaults={"code_iso": p["code_iso"]})
    pays_objs[p["nom"]] = obj

# Assign existing Localites to Senegal
senegal = pays_objs["Sénégal"]
Localite.objects.filter(pays__isnull=True).update(pays=senegal)

# Create new Localites for other countries
localites_autres = [
    {"nom": "Sikasso", "pays": "Mali", "latitude": 11.317, "longitude": -5.666},
    {"nom": "Ségou", "pays": "Mali", "latitude": 13.431, "longitude": -6.215},
    {"nom": "Korhogo", "pays": "Côte d'Ivoire", "latitude": 9.458, "longitude": -5.629},
    {"nom": "Bouaké", "pays": "Côte d'Ivoire", "latitude": 7.693, "longitude": -5.030},
    {"nom": "Bobo-Dioulasso", "pays": "Burkina Faso", "latitude": 11.177, "longitude": -4.297},
    {"nom": "Dédougou", "pays": "Burkina Faso", "latitude": 12.463, "longitude": -3.463},
    {"nom": "Kankan", "pays": "Guinée", "latitude": 10.385, "longitude": -9.305},
    {"nom": "Nzérékoré", "pays": "Guinée", "latitude": 7.756, "longitude": -8.817},
]

for loc in localites_autres:
    p_obj = pays_objs[loc["pays"]]
    obj, created = Localite.objects.get_or_create(
        nom=loc["nom"],
        defaults={
            "pays": p_obj,
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "type_sol": "Non spécifié",
            "conditions_meteo": "Typique de la région"
        }
    )
    if not created and obj.pays is None:
        obj.pays = p_obj
        obj.save()

print("Pays et Agropoles de l'Afrique de l'Ouest ajoutés avec succès.")
