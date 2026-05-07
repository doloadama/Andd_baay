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
from django.http import HttpResponse


_DEFAULT_TTL = 60
_DEFAULT_EXEMPT: list[str] = []
_SAFE_HEADERS = {"Content-Language"}


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
            return self._rehydrate_response(cached)

        response = self.get_response(request)

        if response.status_code == 200 and not response.has_header("Set-Cookie"):
            cache.set(cache_key, self._dehydrate_response(response), self.ttl)

        return response

    def _is_cacheable(self, request) -> bool:
        if request.method != "GET":
            return False
        if request.headers.get("HX-Request") != "true":
            return False
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
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
        user = getattr(request, "user", None)
        user_pk = getattr(user, "pk", None) if user is not None else None
        path = request.path.replace("/", "_").strip("_")
        return f"htmx:{user_pk}:{path}:{qs_hash}"

    @staticmethod
    def _dehydrate_response(response: HttpResponse) -> dict:
        headers = {k: v for (k, v) in response.items() if k in _SAFE_HEADERS}
        return {
            "status": int(getattr(response, "status_code", 200)),
            "content_type": str(getattr(response, "headers", {}).get("Content-Type") or response.get("Content-Type", "text/html; charset=utf-8")),
            "headers": headers,
            "content": bytes(response.content),
        }

    @staticmethod
    def _rehydrate_response(payload: dict) -> HttpResponse:
        resp = HttpResponse(
            payload.get("content", b""),
            status=int(payload.get("status", 200)),
            content_type=payload.get("content_type") or "text/html; charset=utf-8",
        )
        for k, v in (payload.get("headers") or {}).items():
            resp[k] = v
        return resp
