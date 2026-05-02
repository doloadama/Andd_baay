"""Petites CBV génériques (hors urls dédiées métier).

La page hors-ligne n’envoie pas de messages contrib : évite une dépendance
inutile au framework messages lorsque le navigateur est déjà offline.
"""

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView


class OfflineView(TemplateView):
    template_name = "offline.html"


@require_GET
def assetlinks_json(request):
    """Sert /.well-known/assetlinks.json pour Digital Asset Links / TWA (Play Store).

    Tant que ANDROID_PACKAGE_NAME ou les empreintes SHA-256 ne sont pas définis,
    renvoie une liste JSON vide ``[]`` (fichier valide, association inactive).
    """
    package = getattr(settings, "ANDROID_PACKAGE_NAME", "") or ""
    raw = getattr(settings, "ANDROID_ASSETLINKS_SHA256", "") or ""
    separators = [",", "\n", ";"]
    for sep in separators[1:]:
        raw = raw.replace(sep, separators[0])
    fingerprints = [p.strip() for p in raw.split(separators[0]) if p.strip()]

    if package and fingerprints:
        payload = [
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": package,
                    "sha256_cert_fingerprints": fingerprints,
                },
            }
        ]
    else:
        payload = []

    response = JsonResponse(payload, safe=False, json_dumps_params={"indent": 2})
    response["Cache-Control"] = "public, max-age=3600"
    return response
