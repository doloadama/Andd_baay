from urllib.parse import urljoin

from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.views.generic import RedirectView
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from django.contrib.sitemaps.views import sitemap as sitemap_view

from Andd_Baayi import settings
from baay.sitemaps import sitemaps as baay_sitemaps
from baay.views import robots_txt


def health_check(request):
    """Endpoint de santé pour Railway (healthcheckPath) et monitoring externe."""
    return JsonResponse({"status": "ok"}, status=200)

_favicon_url = urljoin(settings.STATIC_URL, 'icons/favicon-32x32.png')

urlpatterns = [
    # Health check — Railway, Uptime Robot, monitoring externe (hors i18n pour éviter les redirects)
    path('health/', health_check, name='health_check'),
    # SEO — robots.txt + sitemap.xml à la racine (hors i18n, sans préfixe de langue)
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_view, {'sitemaps': baay_sitemaps}, name='sitemap'),
    # ── API mobile — JWT auth (hors i18n) ────────────────────────────────────
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    # ── API mobile v1 ─────────────────────────────────────────────────────────
    path('', include('baay.urls_api_mobile')),
    path(
        'favicon.png',
        RedirectView.as_view(url=_favicon_url, permanent=False),
    ),
    path(
        'favicon.ico',
        RedirectView.as_view(url=_favicon_url, permanent=False),
    ),
    path('i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('baay.urls')),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    from baay.views import page_not_found_preview

    urlpatterns.append(
        path('__preview__/404/', page_not_found_preview, name='preview_404'),
    )

if getattr(settings, 'DEBUG_TOOLBAR_ENABLED', False):
    urlpatterns.append(path('__debug__/', include('debug_toolbar.urls')))

handler404 = 'baay.views.page_not_found_view'
