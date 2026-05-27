from django.urls import path

from baay.views_assistant_vocal import assistant_vocal

urlpatterns = [
    path("assistant-vocal/", assistant_vocal, name="assistant_vocal"),
]
