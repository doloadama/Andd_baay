"""
Rate limiting utilities using Django cache.
"""
import hashlib
import time
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


def _get_client_ip(request):
    """Get the real client IP from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "")
    return ip


def _make_rate_limit_key(prefix: str, request, user_id=None) -> str:
    """Create a unique key for rate limiting."""
    if user_id:
        identifier = f"user:{user_id}"
    else:
        ip = _get_client_ip(request)
        # Hash IP for privacy
        identifier = hashlib.sha256(ip.encode()).hexdigest()[:16]
    return f"rate_limit:{prefix}:{identifier}"


def check_rate_limit(request, prefix: str, max_requests: int, window_seconds: int):
    """
    Check if request should be rate limited.
    Returns (allowed: bool, remaining: int, reset_after: int)
    """
    user_id = getattr(request.user, "id", None)
    key = _make_rate_limit_key(prefix, request, user_id)

    now = time.time()
    window_start = now - window_seconds

    # Get current count from cache
    data = cache.get(key, {"count": 0, "window_start": now})

    # Reset if window expired
    if data["window_start"] < window_start:
        data = {"count": 0, "window_start": now}

    count = data["count"]

    # Check limit
    if count >= max_requests:
        reset_after = int(window_seconds - (now - data["window_start"]))
        return False, 0, max(1, reset_after)

    # Increment count
    data["count"] = count + 1
    cache.set(key, data, timeout=window_seconds)

    remaining = max_requests - data["count"]
    return True, remaining, 0


def rate_limit(
    prefix: str,
    max_requests: int = None,
    window_seconds: int = None,
    get_config: callable = None,
):
    """
    Decorator to rate limit a view.

    Usage:
        @rate_limit("chatbot", max_requests=10, window_seconds=60)
        def my_view(request):
            ...

    Or with settings-based config:
        @rate_limit("chatbot", get_config=lambda: settings.CHATBOT_RATE_LIMIT)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Get configuration
            config = None
            if get_config:
                config = get_config()
            elif max_requests and window_seconds:
                config = {"max_requests": max_requests, "window_seconds": window_seconds}

            if config:
                allowed, remaining, reset_after = check_rate_limit(
                    request,
                    prefix,
                    config["max_requests"],
                    config["window_seconds"],
                )
                if not allowed:
                    return JsonResponse(
                        {
                            "error": f"Trop de requêtes. Réessayez dans {reset_after} secondes.",
                            "retry_after": reset_after,
                        },
                        status=429,
                        headers={"Retry-After": str(reset_after)},
                    )

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator
