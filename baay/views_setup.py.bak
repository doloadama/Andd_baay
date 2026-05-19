"""
Temporary setup view for Vercel (no shell available).
Call once with ?token=YOUR_SECRET to initialize the database.
DELETE this file after setup is complete.
"""
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sites.models import Site
from django.conf import settings


@csrf_exempt
def setup_google_oauth_view(request):
    token = request.GET.get('token', '')
    expected = os.getenv('SETUP_SECRET', '')
    if not expected or token != expected:
        return JsonResponse({'error': 'Invalid or missing token'}, status=403)

    from allauth.socialaccount.models import SocialApp

    client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()

    if not client_id or not secret:
        return JsonResponse({'error': 'GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set'}, status=500)

    site_domain = os.getenv('SITE_DOMAIN', '')
    if not site_domain:
        for host in settings.ALLOWED_HOSTS:
            if host not in ('localhost', '127.0.0.1') and not host.startswith('.'):
                site_domain = host
                break
    if not site_domain:
        site_domain = request.get_host()

    site, _ = Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={'domain': site_domain, 'name': 'Andd Baay'}
    )

    app, created = SocialApp.objects.update_or_create(
        provider='google',
        defaults={
            'name': 'Google',
            'client_id': client_id,
            'secret': secret,
            'key': '',
        }
    )

    if site not in app.sites.all():
        app.sites.add(site)

    return JsonResponse({
        'status': 'ok',
        'action': 'created' if created else 'updated',
        'site_domain': site.domain,
        'client_id_prefix': client_id[:20] + '...',
    })
