"""
Callbacks Unfold (configuration via Andd_Baayi.settings).
"""

from django.conf import settings


def unfold_environment_title_prefix(request):
    """Préfixe optionnel dans la balise <title> du back-office."""
    return getattr(settings, "DJANGO_DEPLOY_TITLE_PREFIX", "") or ""


def unfold_environment_badge(request):
    """Badge en-tête : (libellé, variante Tailwind/Unfold pour label.html)."""
    labels = getattr(settings, "DJANGO_DEPLOY_LABELS")
    code = getattr(settings, "DJANGO_DEPLOY_ENV", "development").lower()
    row = labels.get(code) or labels.get("default") or ("Inconnu", "primary")
    return row[0], row[1]
