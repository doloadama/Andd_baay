"""
HtmxCacheMiddleware — cache serveur pour les fragments HTMX.

- Ne cache que les requêtes GET portant l'en-tête HX-Request.
- Clé de cache : htmx:{user.pk}:{path}:{qs_hash}
- TTL configurable via settings.HTMX_CACHE_TTL (défaut : 60 s).
- Chemins exemptés via settings.HTMX_CACHE_EXEMPT_PATHS (liste de préfixes).
"""

import hashlib

from django.conf import settings
from django.core.cache import cache


_DEFAULT_TTL = 60
_DEFAULT_EXEMPT: list[str] = []


class HtmxCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.ttl: int = getattr(settings, "HTMX_CACHE_TTL", _DEFAULT_TTL)
        self.exempt: list[str] = getattr(settings, "HTMX_CACHE_EXEMPT_PATHS", _DEFAULT_EXEMPT)

    def __call__(self, request):
        if not self._is_cacheable(request):
            return self.get_response(request)

        cache_key = self._build_key(request)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        response = self.get_response(request)

        if response.status_code == 200:
            cache.set(cache_key, response, self.ttl)

        return response

    def _is_cacheable(self, request) -> bool:
        if request.method != "GET":
            return False
        if request.headers.get("HX-Request") != "true":
            return False
        if not request.user.is_authenticated:
            return False
        path = request.path
        for exempt_prefix in self.exempt:
            if path.startswith(exempt_prefix):
                return False
        return True

    @staticmethod
    def _build_key(request) -> str:
        qs = request.META.get("QUERY_STRING", "")
        qs_hash = hashlib.md5(qs.encode(), usedforsecurity=False).hexdigest()[:8]
        user_pk = request.user.pk
        path = request.path.replace("/", "_").strip("_")
        return f"htmx:{user_pk}:{path}:{qs_hash}"
