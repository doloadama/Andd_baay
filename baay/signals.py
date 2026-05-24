import logging

from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models.signals import post_migrate, post_save
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
        trigger = {"date_semis", "superficie_allouee", "produit", "etat_vegetatif"}
        if not trigger.intersection(update_fields):
            return
    update_prediction_for_projet_produit(instance)


@receiver(post_save, sender=ProjetProduit)
def valider_label_ml_a_cloture(sender, instance, update_fields=None, **kwargs):
    """P4.3 — Renseigne rendement_reel et erreur_pct dans PrevisionFeatures
    dès que rendement_final est enregistré (clôture du projet).
    Invalide aussi le cache des correcteurs de biais pour que le prochain
    refresher_correcteurs_biais_task intègre cette nouvelle observation.
    """
    if kwargs.get("raw"):
        return
    # On n'agit que si rendement_final vient d'être renseigné
    if update_fields is not None and "rendement_final" not in update_fields:
        return
    if not instance.rendement_final:
        return

    try:
        from baay.models import PrevisionFeatures

        prevision = getattr(instance, "prevision", None)
        if prevision is None:
            return
        feats = PrevisionFeatures.objects.filter(prevision=prevision).first()
        if feats is None:
            return

        reel = float(instance.rendement_final)
        mid = (prevision.rendement_estime_min + prevision.rendement_estime_max) / 2.0
        erreur = (mid - reel) / reel * 100.0 if reel else None

        from django.utils import timezone
        feats.rendement_reel = reel
        feats.erreur_pct = round(erreur, 4) if erreur is not None else None
        feats.date_validation = timezone.now()
        feats.save(update_fields=["rendement_reel", "erreur_pct", "date_validation"])

        # Invalider le cache des correcteurs → intégré au prochain refresh Beat (6h)
        from baay.services.prediction_accuracy import invalider_cache_correcteurs_biais
        invalider_cache_correcteurs_biais()

        # ── Déclenchement auto-réentraînement ──────────────────────────────
        # Si cette culture a accumulé MIN_NEW_OBS_AUTO nouveaux labels depuis
        # le dernier entraînement, on lance la tâche immédiatement (async).
        try:
            from baay.services.ml_training import (
                MIN_NEW_OBS_AUTO,
                cultures_a_reentrainer,
            )
            from baay.tasks import auto_retrain_models_task

            culture_nom = getattr(
                getattr(instance, "produit", None), "nom", None
            )
            if culture_nom:
                a_reentrainer = cultures_a_reentrainer(min_new_obs=MIN_NEW_OBS_AUTO)
                if culture_nom in a_reentrainer:
                    auto_retrain_models_task.delay(
                        declencheur="signal",
                        min_new_obs=MIN_NEW_OBS_AUTO,
                        min_n=5,
                    )
                    logger.info(
                        "valider_label_ml : auto-réentraînement déclenché pour '%s'.",
                        culture_nom,
                    )
        except Exception as exc_retrain:
            logger.warning(
                "valider_label_ml : vérification auto-retrain échouée : %s", exc_retrain
            )

    except Exception as exc:
        logger.warning("valider_label_ml_a_cloture : erreur pour pp=%s : %s", instance.pk, exc)


@receiver(post_migrate)
def sync_google_oauth_site_domain(sender, **kwargs):
    """Aligne django.contrib.sites sur l'hôte OAuth (local vs prod)."""
    if getattr(sender, "name", None) != "sites":
        return
    try:
        from baay.google_oauth_site import ensure_site_domain

        domain = ensure_site_domain()
        logger.info("OAuth Site domain synchronise: %s", domain)
    except Exception:
        logger.exception("Impossible de synchroniser le domaine Site pour Google OAuth")
