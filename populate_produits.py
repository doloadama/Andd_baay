import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Andd_Baayi.settings')
django.setup()

from baay.models import ProduitAgricole

produits = [
    {"nom": "Riz", "description": "Culture principale", "rendement_moyen": 4500},
    {"nom": "Maïs", "description": "Céréale polyvalente", "rendement_moyen": 3000},
    {"nom": "Mil", "description": "Résistant à la sécheresse", "rendement_moyen": 1500},
    {"nom": "Sorgho", "description": "Sorgho local", "rendement_moyen": 1800},
    {"nom": "Arachide", "description": "Culture de rente importante", "rendement_moyen": 1200},
    {"nom": "Niébé", "description": "Légumineuse riche en protéines", "rendement_moyen": 800},
    {"nom": "Oignon", "description": "Culture maraîchère", "rendement_moyen": 25000},
    {"nom": "Tomate", "description": "Légume fruit", "rendement_moyen": 20000},
]

for p in produits:
    ProduitAgricole.objects.get_or_create(nom=p['nom'], defaults=p)

print("Produits ajoutés avec succès.")
