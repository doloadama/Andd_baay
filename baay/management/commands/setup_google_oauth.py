"""
Management command: python manage.py setup_google_oauth
Creates or updates the Google SocialApp entry in the database.
Run this once after setting GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env
"""
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = 'Configure Google OAuth SocialApp in the database'

    def handle(self, *args, **options):
        from allauth.socialaccount.models import SocialApp

        client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
        secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()

        if not client_id or not secret:
            self.stderr.write(self.style.ERROR(
                '❌  GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in your .env file.'
            ))
            return

        # Determine correct domain for the Site
        site_domain = os.getenv('SITE_DOMAIN', '').strip()
        if not site_domain:
            # Use first production-looking host from ALLOWED_HOSTS as fallback
            for host in settings.ALLOWED_HOSTS:
                if host not in ('localhost', '127.0.0.1') and not host.startswith('.'):
                    site_domain = host
                    break
        if not site_domain:
            site_domain = '127.0.0.1:8000'

        # Ensure Site exists (SITE_ID=1) with correct domain
        site, _ = Site.objects.update_or_create(
            pk=settings.SITE_ID,
            defaults={'domain': site_domain, 'name': 'Andd Baay'}
        )

        # Create or update the SocialApp
        app, created = SocialApp.objects.update_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': client_id,
                'secret': secret,
                'key': '',
            }
        )

        # Attach to the current site
        if site not in app.sites.all():
            app.sites.add(site)

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'✅  {action} Google SocialApp successfully.\n'
            f'    Client ID : {client_id[:20]}...\n'
            f'    Site      : {site.domain} (ID={site.pk})\n\n'
            f'👉  Now visit /login/ and click "Continuer avec Google" to test.'
        ))
