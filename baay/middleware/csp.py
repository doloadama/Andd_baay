from django.conf import settings
import os
import secrets


def _bool_env(name: str, default: str = "False") -> bool:
    return str(getattr(settings, name, default)).lower() in ("1", "true", "yes")


class ContentSecurityPolicyMiddleware:
    """
    CSP header aligné sur la stack frontend après vendorisation (perf-audit.md) :
    Bootstrap, Chart.js, ApexCharts, HTMX, Alpine, Font Awesome et Leaflet sont
    tous servis en local depuis /static/. Le seul tiers HTTPS restant est Google
    Fonts (CSS) + l'outillage Figma MCP en dev.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.has_header("Content-Security-Policy") or response.has_header("Content-Security-Policy-Report-Only"):
            return response

        is_production = getattr(settings, "ENV", "").lower() == "production" or getattr(settings, "IS_VERCEL", False)

        # Alpine et certains widgets inline ont besoin de 'unsafe-inline' / 'unsafe-eval'.
        # Pour les supprimer, il faudra migrer vers une nonce/hash (CSP_INCLUDE_NONCE prévu plus bas).
        script_src = [
            "'self'",
            "'unsafe-inline'",
        ]
        if not is_production:
            # unsafe-eval uniquement en dev (pour Alpine et outils)
            script_src.append("'unsafe-eval'")
            # Figma MCP uniquement en dev
            script_src.append("https://mcp.figma.com")

        connect_src = ["'self'"]
        if not is_production:
            connect_src.append("https://mcp.figma.com")

        policy = {
            "default-src": ["'self'"],
            "base-uri": ["'self'"],
            "object-src": ["'none'"],
            "frame-ancestors": ["'none'"],
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'", "https:", "data:"],
            "style-src": [
                "'self'",
                "'unsafe-inline'",
                "https://fonts.googleapis.com",
            ],
            "script-src": script_src,
            "connect-src": connect_src,
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

