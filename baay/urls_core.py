from django.urls import path
from django.views.generic import TemplateView

from .views_core import dashboard, home_view, profil_view

urlpatterns = [
    path("", home_view, name="home"),
    path("offline/", TemplateView.as_view(template_name="offline.html"), name="offline"),
    path("dashboard/", dashboard, name="dashboard"),
    path("profil/", profil_view, name="profil"),
]
