import logging

from django.contrib import messages
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from baay.models import Ferme, Investissement, MembreFerme, Projet, ProjetProduit
from baay.middleware.current_request import get_current_request
from baay.permissions import peut_acceder_menu_finance, peut_modifier_budget_ferme
from baay.services import ensure_profile_for_user, update_prediction_for_projet_produit, check_budget_status

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

@receiver(post_save, sender=Investissement)
def alerte_depassement_budget_investissement(sender, instance, **kwargs):
    """Avertissement utilisateur si le cumul investissements dépasse budget_alloue."""
    if kwargs.get("raw"):
        return
    status = check_budget_status(instance.projet_id)
    if not status.get("ok") or not status.get("applicable") or not status.get("over_budget"):
        return

    request = get_current_request()
    if not request or not getattr(request, "user", None) or not request.user.is_authenticated:
        return

    profile = getattr(request.user, "profile", None)
    if not profile:
        return
    if not peut_acceder_menu_finance(profile):
        return
    if not peut_modifier_budget_ferme(profile, instance.projet.ferme):
        return

    msg = (
        f"Attention : Le budget du projet « {status['projet_nom']} » est dépassé de "
        f"{status['depassement_display']} FCFA."
    )
    messages.warning(request, msg, extra_tags="budget-critical")


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

