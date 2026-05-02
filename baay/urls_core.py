from django.urls import path

from .generic_views import OfflineView, assetlinks_json
from .views_core import (
    dashboard,
    home_view,
    onboarding_complete_view,
    onboarding_wizard_view,
    profil_view,
)

urlpatterns = [
    path(".well-known/assetlinks.json", assetlinks_json, name="assetlinks_json"),
    path("", home_view, name="home"),
    path("offline/", OfflineView.as_view(), name="offline"),
    path("dashboard/", dashboard, name="dashboard"),
    path("onboarding/", onboarding_wizard_view, name="onboarding"),
    path("onboarding/terminer/", onboarding_complete_view, name="onboarding_complete"),
    path("profil/", profil_view, name="profil"),
]
