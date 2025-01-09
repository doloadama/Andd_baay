from django.urls import path
from .views import signup, user_login, password_reset_request, password_reset_confirm

urlpatterns = [
    path('signup/', signup, name='signup'),
    path('login/', user_login, name='login'),
    path('password-reset/', password_reset_request, name='password_reset_request'),
    path('password-reset-confirm/<str:token>/', password_reset_confirm, name='password_reset_confirm'),
]