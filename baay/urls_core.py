from django.urls import path

from .generic_views import OfflineView
from .views_core import dashboard, home_view, profil_view

urlpatterns = [
    path("", home_view, name="home"),
    path("offline/", OfflineView.as_view(), name="offline"),
    path("dashboard/", dashboard, name="dashboard"),
    path("profil/", profil_view, name="profil"),
]
