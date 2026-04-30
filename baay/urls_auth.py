from django.contrib.auth import views as auth_views
from django.urls import path

from .views_auth import (
    CustomPasswordResetConfirmView,
    CustomPasswordResetView,
    confirm_email_view,
    login_view,
    logout_view,
    register_view,
)

urlpatterns = [
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("confirm-email/<uidb64>/<token>/", confirm_email_view, name="confirm_email"),
    path("logout/", logout_view, name="logout"),
    path("password_reset/", CustomPasswordResetView.as_view(), name="password_reset"),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="auth/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        CustomPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="auth/password_reset_complete.html"),
        name="password_reset_complete",
    ),
]
