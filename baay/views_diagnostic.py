import logging

from django.core.cache import cache
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from baay.services.plant_vision.analyzer import PlantVisionError, analyze_plant_pest

logger = logging.getLogger(__name__)

CULTURES = [
    ("mil", "Mil"),
    ("arachide", "Arachide"),
    ("sorgho", "Sorgho"),
    ("mais", "Maïs"),
    ("riz", "Riz"),
    ("niebe", "Niébé"),
    ("manioc", "Manioc"),
    ("tomate", "Tomate"),
    ("oignon", "Oignon"),
    ("piment", "Piment"),
    ("coton", "Coton"),
    ("autre", "Autre culture"),
]

_CULTURES_MAP = dict(CULTURES)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
RATE_LIMIT = 5  # analyses per IP per 10 minutes
RATE_WINDOW = 600  # seconds


def _check_rate_limit(ip: str) -> bool:
    """Return True if IP is within the allowed rate."""
    key = f"diag_rl:{ip}"
    count = cache.get(key, 0)
    if count >= RATE_LIMIT:
        return False
    cache.set(key, count + 1, RATE_WINDOW)
    return True


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


@require_http_methods(["GET", "POST"])
def diagnostic_rapide(request):
    context = {"cultures": CULTURES}

    if request.method == "POST":
        photo = request.FILES.get("photo")
        culture_key = request.POST.get("culture", "autre")
        culture_label = _CULTURES_MAP.get(culture_key, culture_key)
        context["culture_key"] = culture_key
        context["culture_label"] = culture_label

        error = None

        if not photo:
            error = "Veuillez joindre une photo de votre culture."
        elif photo.size > MAX_FILE_SIZE:
            error = "La photo est trop lourde (max 10 Mo). Réduisez la taille et réessayez."
        elif photo.content_type not in ALLOWED_MIME:
            error = "Format non supporté. Utilisez JPEG, PNG ou WebP."
        elif not _check_rate_limit(_client_ip(request)):
            error = "Trop d'analyses récentes depuis votre réseau. Réessayez dans quelques minutes."

        if error:
            context["form_error"] = error
        else:
            image_bytes = photo.read()
            content_type = photo.content_type
            try:
                resultat = analyze_plant_pest(
                    image_bytes,
                    content_type,
                    crop_name=culture_label,
                    upload_crops=True,
                )
                context["analyse_statut"] = "terminee"
                context["analyse_resultat"] = resultat
            except PlantVisionError as exc:
                context["analyse_statut"] = "echec"
                context["analyse_erreur"] = str(exc)
            except Exception as exc:
                logger.exception("Erreur inattendue diagnostic_rapide")
                context["analyse_statut"] = "echec"
                context["analyse_erreur"] = "Une erreur est survenue. Réessayez avec une photo plus nette."

    return render(request, "diagnostic/index.html", context)
