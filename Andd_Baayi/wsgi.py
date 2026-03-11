"""
WSGI config for Andd_Baayi project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
import sys

# Add project directory to path for Vercel
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Andd_Baayi.settings')

application = get_wsgi_application()

# Vercel requires 'app' as the handler
app = application
