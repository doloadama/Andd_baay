from urllib.parse import urljoin

from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.views.generic import RedirectView

from Andd_Baayi import settings

_favicon_url = urljoin(settings.STATIC_URL, 'icons/favicon-32x32.png')

urlpatterns = [
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
