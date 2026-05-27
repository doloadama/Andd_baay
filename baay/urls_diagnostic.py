from django.urls import path

from baay.views_diagnostic import diagnostic_rapide

urlpatterns = [
    path("diagnostic/", diagnostic_rapide, name="diagnostic_rapide"),
]
