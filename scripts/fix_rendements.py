import os
import django

# Configuration de l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Andd_Baayi.settings')
django.setup()

from baay.models import Projet
from baay.views import predire_rendement

print("Démarrage du calcul des rendements pour les projets existants...")
projets = Projet.objects.all()
count = 0

for projet in projets:
    if not projet.rendement_estime or projet.rendement_estime == 0:
        rendement = predire_rendement(projet)
        projet.rendement_estime = rendement
        projet.save(update_fields=['rendement_estime'])
        print(f"✅ Projet '{projet.nom}' mis à jour avec le rendement : {rendement} kg")
        count += 1
    else:
        print(f"⏭️ Projet '{projet.nom}' a déjà un rendement : {projet.rendement_estime} kg")

print(f"Terminé. {count} projets mis à jour.")
