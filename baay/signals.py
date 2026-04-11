import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from baay.models import Profile, Projet, PrevisionRecolte

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile instance whenever a new User is created."""
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the Profile instance whenever the User is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()

@receiver(post_save, sender=Projet)
def creer_prediction_rendement_projet(sender, instance, created, **kwargs):
    """Fallback if needed for legacy logic."""
    pass

from baay.models import ProjetProduit, PrevisionRecolte
from baay.services import estimer_rendement_ia

@receiver(post_save, sender=ProjetProduit)
def update_prediction_rendement(sender, instance, created, **kwargs):
    """Mettre à jour l'estimation dynamique sur modification d'une culture."""
    
    # Appel de l'IA (Orchestrateur)
    resultats = estimer_rendement_ia(instance)
    
    # 3. Sauvegarde dans PrevisionRecolte lié au projet principal
    prediction, _ = PrevisionRecolte.objects.get_or_create(projet=instance.projet)
    prediction.rendement_estime_min = resultats['min']
    prediction.rendement_estime_max = resultats['max']
    prediction.indice_confiance = resultats['confiance']
    prediction.date_recolte_prevue = resultats['date_recolte_prevue']
    prediction.save()


