from django.urls import path
from .views import signup, user_login, password_reset_confirm

urlpatterns = [
    path('signup/', signup, name='signup'),
    path('login/', user_login, name='login'),

    path('password-reset-confirm/', password_reset_confirm, name='password_reset_confirm'),
]