import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'baay.settings')
django.setup()
from baay.models import Pays, Region, Localite
mali = Pays.objects.filter(nom='Mali').first()
print(f'Mali exists: {mali is not None}')
if mali:
    regions = Region.objects.filter(pays=mali).count()
    localities = Localite.objects.filter(pays=mali).count()
    print(f'Regions: {regions}')
    print(f'Localities: {localities}')
