import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from baay.models import Profile, Projet, PredictionRendement

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

from baay.models import ProjetProduit
from baay.services import calculer_indice_confiance, predict_rendement_ml

@receiver(post_save, sender=ProjetProduit)
def update_prediction_rendement(sender, instance, created, **kwargs):
    """Mettre à jour l'indice de confiance et le rendement estimé à chaque modification des paramètres agricoles."""
    # 1. Calcul de l'indice de confiance
    confiance = calculer_indice_confiance(instance)
    
    # 2. Prédiction IA
    # Features stub pour le ML
    features = {
        'superficie': float(instance.superficie_allouee or 1),
        'semences_kg': float(instance.quantite_semences or 0),
        'type_sol': instance.projet.localite.type_sol
    }
    rendement_estime = predict_rendement_ml(features)
    
    # 3. Sauvegarde dans PredictionRendement lié au projet principal
    prediction, _ = PredictionRendement.objects.get_or_create(projet=instance.projet, defaults={'rendement_estime': 0})
    prediction.rendement_estime = rendement_estime
    prediction.indice_confiance = confiance
    prediction.save()

