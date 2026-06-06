# baay/urls_calendrier.py — pages publiques du calendrier cultural (SEO).
from django.urls import path

from .views_calendrier import calendrier_detail, calendrier_liste

urlpatterns = [
    path("calendrier-cultural/", calendrier_liste, name="calendrier"),
    path("calendrier-cultural/<slug:slug>/", calendrier_detail, name="calendrier_detail"),
]
