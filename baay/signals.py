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
def creer_prediction_rendement(sender, instance, created, **kwargs):
    """Generate a yield prediction when a new project is created."""
    if created:
        from baay.views import predire_rendement
        logger.debug(f"Signal triggered for project {instance.id}")
        rendement_pred = predire_rendement(instance)
        PredictionRendement.objects.create(projet=instance, rendement_estime=rendement_pred)
