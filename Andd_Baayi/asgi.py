"""
ASGI config for Andd_Baayi project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Andd_Baayi.settings')

application = get_asgi_application()
