from django.urls import include, path

urlpatterns = [
    path("", include("baay.urls_finance")),
    path("", include("baay.urls_core")),
    path("", include("baay.urls_auth")),
    path("", include("baay.urls_projets")),
    path("", include("baay.urls_semis")),
    path("", include("baay.urls_fermes")),
    path("", include("baay.urls_taches")),
    path("", include("baay.urls_commentaires")),
    path("", include("baay.urls_api")),
    path("", include("baay.urls_dashboard")),
    path("", include("baay.urls_carte")),
    path("", include("baay.urls_sols")),
    path("", include("baay.urls_diagnostic")),
    path("", include("baay.urls_assistant_vocal")),
    path("", include("baay.urls_invitations")),
    path("", include("baay.urls_cooperative")),
    path("", include("baay.urls_actualites")),
    path("", include("baay.urls_marche")),
]