from django.urls import path

from baay.views_diagnostic import diagnostic_rapide, diagnostic_result

urlpatterns = [
    path("diagnostic/", diagnostic_rapide, name="diagnostic_rapide"),
    path("diagnostic/<slug:culture>/", diagnostic_rapide, name="diagnostic_culture"),
    path("diagnostic/result/<str:task_id>/", diagnostic_result, name="diagnostic_result"),
]
