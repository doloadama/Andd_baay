import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Andd_Baayi.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

apps = list(SocialApp.objects.filter(provider='google').order_by('id'))
print(f"SocialApp Google count: {len(apps)}")
for a in apps:
    cid = (a.client_id or '')[:30]
    print(f"  ID={a.id} | name={a.name} | client_id={cid}...")

if len(apps) > 1:
    # Keep the last one (most recent with real credentials), delete the rest
    to_keep = apps[-1]
    to_delete = apps[:-1]
    print(f"\nKeeping ID={to_keep.id}")
    for a in to_delete:
        print(f"Deleting ID={a.id}")
        a.delete()
    # Ensure it's linked to site 1
    site, _ = Site.objects.get_or_create(id=1, defaults={'domain': '127.0.0.1:8000', 'name': 'Andd Baay'})
    if site not in to_keep.sites.all():
        to_keep.sites.add(site)
    print("Done — duplicate removed.")
elif len(apps) == 1:
    print("Only one entry, no duplicates to remove.")
else:
    print("No Google SocialApp found.")
