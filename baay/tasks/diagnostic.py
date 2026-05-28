import logging

from celery import shared_task
from django.core.cache import cache

from baay.services.plant_vision.analyzer import analyze_plant_pest, image_content_hash, PlantVisionError

logger = logging.getLogger(__name__)

CACHE_TTL = 60 * 60 * 24 * 7  # 7 days


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def analyze_plant_pest_task(self, image_bytes_hex: str, content_type: str,
                             culture_label: str, langue: str, task_cache_key: str):
    """
    Analyse une image de plante via Gemini de maniere asynchrone.
    Stocke le resultat dans le cache Django sous task_cache_key.
    """
    try:
        image_bytes = bytes.fromhex(image_bytes_hex)

        # Check image-level cache first
        h = image_content_hash(image_bytes)
        cached = cache.get(f"bv:{h}:{langue}")
        if cached is not None:
            logger.info("analyze_plant_pest_task: cache hit")
            cache.set(task_cache_key, {"status": "done", "result": cached}, 3600)
            try:
                from baay.models import AppelAPILog
                from django.conf import settings
                model = getattr(settings, "PLANT_VISION_MODEL", "gemini-2.0-flash")
                AppelAPILog.objects.create(service="gemini", modele=model, cache_hit=True)
            except Exception:
                pass
            return

        result = analyze_plant_pest(
            image_bytes,
            content_type,
            crop_name=culture_label,
            upload_crops=True,
            language=langue,
        )
        # Store in image-level cache
        cache.set(f"bv:{h}:{langue}", result, CACHE_TTL)
        # Store task result
        cache.set(task_cache_key, {"status": "done", "result": result}, 3600)

    except PlantVisionError as exc:
        cache.set(task_cache_key, {"status": "error", "error": str(exc)}, 3600)
    except Exception as exc:
        logger.exception("Unexpected error in analyze_plant_pest_task")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            cache.set(task_cache_key, {
                "status": "error",
                "error": "Analyse impossible apres plusieurs tentatives. Reessayez."
            }, 3600)
