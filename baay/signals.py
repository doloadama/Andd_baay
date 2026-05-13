import logging

from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from baay.middleware.current_request import get_current_request
from baay.models import Ferme, Investissement, MembreFerme, Projet, ProjetProduit
from baay.permissions import peut_acceder_menu_finance, peut_modifier_budget_ferme
from baay.services import (
    check_budget_status,
    check_projet_produit_budget_status,
    ensure_profile_for_user,
    update_prediction_for_projet_produit,
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile instance whenever a new User is created."""
    if created:
        ensure_profile_for_user(instance)


@receiver(post_save, sender=Ferme)
def creer_membre_proprietaire_apres_ferme(sender, instance, created, **kwargs):
    """Le propriétaire est tracé uniquement via Ferme.proprietaire.
    Aucune ligne MembreFerme n'est créée pour le propriétaire."""
    pass


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    """Save existing profile on user updates without redundant create/fetch."""
    if created:
        return
    if hasattr(instance, "profile"):
        instance.profile.save()


@receiver(post_save, sender=Projet)
def creer_prediction_rendement_projet(sender, instance, created, **kwargs):
    """Fallback if needed for legacy logic."""
    pass


@receiver(post_save, sender=Investissement)
def alerte_depassement_budget_investissement(sender, instance, **kwargs):
    """Budget projet ou culture dépassé → toast rouge (messages.error) si requête autorisée."""
    if kwargs.get("raw"):
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

    st = check_budget_status(instance.projet_id)
    if st.get("applicable") and st.get("over_budget"):
        msg = (
            f"Attention : Le budget du projet « {st['projet_nom']} » est dépassé de "
            f"{st['depassement_display']} FCFA."
        )
        messages.error(request, msg, extra_tags="budget-critical")

    if instance.projet_produit_id:
        stp = check_projet_produit_budget_status(instance.projet_produit_id)
        if stp.get("applicable") and stp.get("over_budget"):
            msg = (
                f"Attention : Le budget de la culture « {stp['projet_line_label']} » est dépassé de "
                f"{stp['depassement_display']} FCFA."
            )
            messages.error(request, msg, extra_tags="budget-critical")


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
