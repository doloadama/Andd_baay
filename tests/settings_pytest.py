"""
Pytest settings: force a local SQLite database, regardless of DATABASE_URL.
This avoids hangs / DNS issues when a remote Postgres URL is present in env.
"""

from Andd_Baayi.settings import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Tests should not require external services.
CLOUDINARY_ACTIVE = False
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable SSL redirect for tests to avoid 301 errors
SECURE_SSL_REDIRECT = False

# Axes' standalone backend requires a request during authenticate(),
# which breaks Django's test client `login()` helper.
AXES_ENABLED = False
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

