import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from baay.models import Ferme, MembreFerme, Projet, ProjetProduit
from baay.services import ensure_profile_for_user, update_prediction_for_projet_produit

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile instance whenever a new User is created."""
    if created:
        ensure_profile_for_user(instance)

@receiver(post_save, sender=Ferme)
def creer_membre_proprietaire_apres_ferme(sender, instance, created, **kwargs):
    """Chaque nouvelle ferme a un MembreFerme « Propriétaire » aligné sur Ferme.proprietaire."""
    if not created:
        return
    MembreFerme.objects.get_or_create(
        ferme=instance,
        utilisateur=instance.proprietaire,
        defaults={"role": "proprietaire", "peut_gerer_membres": True},
    )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    """Save existing profile on user updates without redundant create/fetch."""
    if created:
        return
    if hasattr(instance, 'profile'):
        instance.profile.save()

@receiver(post_save, sender=Projet)
def creer_prediction_rendement_projet(sender, instance, created, **kwargs):
    """Fallback if needed for legacy logic."""
    pass

@receiver(post_save, sender=ProjetProduit)
def update_prediction_rendement(sender, instance, created, update_fields=None, **kwargs):
    """Recalcule la prévision IA liée au semis (création ou champs agronomiques modifiés)."""
    if kwargs.get("raw"):
        return
    if not created and update_fields is not None:
        trigger = {"date_semis", "superficie_allouee", "produit"}
        if not trigger.intersection(update_fields):
            return
    update_prediction_for_projet_produit(instance)


