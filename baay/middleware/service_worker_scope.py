"""
Add ``Service-Worker-Allowed: /`` for the app service worker script.

When ``sw.js`` lives under ``/static/js/``, browsers restrict default scope to
that directory. Allowing ``scope: '/'`` at registration requires this header
on the response that serves the worker script.
"""

from urllib.parse import urlparse

from django.conf import settings


def _service_worker_script_path() -> str:
    static_url = getattr(settings, "STATIC_URL", "/static/") or "/static/"
    if static_url.startswith("http"):
        path = urlparse(static_url).path.rstrip("/") or ""
    else:
        path = static_url.rstrip("/")
    if not path:
        path = "/static"
    return f"{path}/js/sw.js"


class ServiceWorkerAllowedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._sw_path = _service_worker_script_path()

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.rstrip("/") == self._sw_path.rstrip("/"):
            response["Service-Worker-Allowed"] = "/"
        return response
