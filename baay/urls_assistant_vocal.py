from django.urls import path

from baay.views_assistant_vocal import assistant_vocal, assistant_vocal_result

urlpatterns = [
    path("assistant-vocal/", assistant_vocal, name="assistant_vocal"),
    path("assistant-vocal/result/<str:task_id>/", assistant_vocal_result,
         name="assistant_vocal_result"),
]
