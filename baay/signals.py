import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from baay.models import Profile, Projet, ProjetProduit
from baay.services import ensure_profile_for_user, update_prediction_for_projet_produit

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile instance whenever a new User is created."""
    if created:
        ensure_profile_for_user(instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the Profile instance whenever the User is saved."""
    profile = ensure_profile_for_user(instance)
    profile.save()

@receiver(post_save, sender=Projet)
def creer_prediction_rendement_projet(sender, instance, created, **kwargs):
    """Fallback if needed for legacy logic."""
    pass

@receiver(post_save, sender=ProjetProduit)
def update_prediction_rendement(sender, instance, created, **kwargs):
    """Mettre à jour l'estimation dynamique sur modification d'une culture."""
    update_prediction_for_projet_produit(instance)


