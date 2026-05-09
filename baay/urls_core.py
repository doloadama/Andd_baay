from django.urls import path

from .generic_views import OfflineView, assetlinks_json
from .views_core import (
    dashboard,
    home_view,
    onboarding_complete_view,
    onboarding_wizard_view,
    profil_view,
)
from .views import (
    dashboard_partial_kpis,
    dashboard_partial_messages,
    dashboard_partial_alertes,
    performance,
    activites,
)

urlpatterns = [
    path(".well-known/assetlinks.json", assetlinks_json, name="assetlinks_json"),
    path("", home_view, name="home"),
    path("offline/", OfflineView.as_view(), name="offline"),
    path("dashboard/", dashboard, name="dashboard"),
    path("dashboard/partial/kpis/", dashboard_partial_kpis, name="dashboard_partial_kpis"),
    path("dashboard/partial/messages/", dashboard_partial_messages, name="dashboard_partial_messages"),
    path("dashboard/partial/alertes/", dashboard_partial_alertes, name="dashboard_partial_alertes"),
    path("performance/", performance, name="performance"),
    path("activites/", activites, name="activites"),
    path("onboarding/", onboarding_wizard_view, name="onboarding"),
    path("onboarding/terminer/", onboarding_complete_view, name="onboarding_complete"),
    path("profil/", profil_view, name="profil"),
]
