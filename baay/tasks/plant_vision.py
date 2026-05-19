import logging

from celery import shared_task
from django.utils import timezone

from baay.models import AnalyseImageCulture
from baay.services.plant_vision import PlantVisionError, analyze_plant_pest
from baay.services.plant_vision.analyzer import fetch_image_from_url, image_content_hash

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=0)
def run_analyse_image_culture(self, analyse_id: str):
    """Tâche Celery : télécharge la photo, appelle Gemini, enregistre le résultat."""
    try:
        analyse = AnalyseImageCulture.objects.select_related(
            "projet_produit__produit",
        ).get(pk=analyse_id)
    except AnalyseImageCulture.DoesNotExist:
        logger.error("Analyse introuvable: %s", analyse_id)
        return

    pp = analyse.projet_produit
    if not pp.image:
        analyse.statut = AnalyseImageCulture.STATUT_ECHEC
        analyse.message_erreur = "Aucune photo sur cette culture."
        analyse.date_fin = timezone.now()
        analyse.save(update_fields=["statut", "message_erreur", "date_fin"])
        return

    analyse.statut = AnalyseImageCulture.STATUT_EN_COURS
    analyse.save(update_fields=["statut"])

    try:
        image_bytes, content_type = fetch_image_from_url(pp.image.url)
        analyse.image_hash = image_content_hash(image_bytes)
        crop_name = pp.produit.nom if pp.produit_id else ""
        result = analyze_plant_pest(
            image_bytes,
            content_type,
            crop_name=crop_name,
        )
        subject = result.get("subject") or {}
        analyse.resultat = result
        analyse.sujet_type = subject.get("subjectType", "")[:32]
        analyse.sujet_description = subject.get("description", "")[:2000]
        analyse.statut = AnalyseImageCulture.STATUT_TERMINEE
        analyse.message_erreur = ""
    except PlantVisionError as exc:
        analyse.statut = AnalyseImageCulture.STATUT_ECHEC
        analyse.message_erreur = str(exc)[:1000]
        logger.warning("Analyse échouée %s: %s", analyse_id, exc)
    except Exception as exc:
        analyse.statut = AnalyseImageCulture.STATUT_ECHEC
        analyse.message_erreur = "Erreur interne lors de l'analyse."
        logger.exception("Analyse image %s", analyse_id)
    finally:
        analyse.date_fin = timezone.now()
        analyse.save()
