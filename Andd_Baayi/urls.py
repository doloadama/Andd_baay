from urllib.parse import urljoin

from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
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
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('baay.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    from baay.views import page_not_found_preview

    urlpatterns.append(
        path('__preview__/404/', page_not_found_preview, name='preview_404'),
    )

handler404 = 'baay.views.page_not_found_view'
