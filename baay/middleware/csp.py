import secrets

from django.conf import settings


def _bool_env(name: str, default: str = "False") -> bool:
    return str(getattr(settings, name, default)).lower() in ("1", "true", "yes")


class ContentSecurityPolicyMiddleware:
    """
    Adds a CSP header that matches our current frontend stack (Bootstrap + Tailwind CDN,
    HTMX + Alpine via self-hosted vendor files, Chart.js via self-hosted vendor files).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.has_header("Content-Security-Policy") or response.has_header("Content-Security-Policy-Report-Only"):
            return response

        # NOTE: We still have Tailwind CDN + inline styles across templates; and Alpine's default build needs unsafe-eval.
        # This policy is "strict" in the sense of blocking objects, restricting sources, and locking down base/frame.
        policy = {
            "default-src": ["'self'"],
            "base-uri": ["'self'"],
            "object-src": ["'none'"],
            "frame-ancestors": ["'none'"],
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'", "https:", "data:"],
            "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
            "script-src": [
                "'self'",
                "'unsafe-inline'",
                "'unsafe-eval'",
                "https://cdn.tailwindcss.com",
            ],
            "connect-src": ["'self'", "https:"],
            "worker-src": ["'self'", "blob:"],
            "manifest-src": ["'self'"],
            "upgrade-insecure-requests": [],
        }

        value = "; ".join(
            f"{k} {' '.join(v)}".strip()
            for k, v in policy.items()
        )

        report_only = getattr(settings, "CSP_REPORT_ONLY", False)
        header_name = "Content-Security-Policy-Report-Only" if report_only else "Content-Security-Policy"
        response[header_name] = value
        response["Cross-Origin-Opener-Policy"] = "same-origin"
        response["Cross-Origin-Resource-Policy"] = "same-origin"

        # Optional per-request nonce (for future migration away from 'unsafe-inline')
        if getattr(settings, "CSP_INCLUDE_NONCE", False):
            request.csp_nonce = secrets.token_urlsafe(16)

        return response

