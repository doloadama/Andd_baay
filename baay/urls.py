from django.urls import include, path

urlpatterns = [
    path("", include("baay.urls_core")),
    path("", include("baay.urls_auth")),
    path("", include("baay.urls_projets")),
    path("", include("baay.urls_semis")),
    path("", include("baay.urls_fermes")),
    path("", include("baay.urls_taches")),
    path("", include("baay.urls_messagerie")),
    path("", include("baay.urls_api")),
]