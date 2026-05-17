import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'baay.settings')
django.setup()
from baay.models import Pays, Region, Localite
mali = Pays.objects.filter(nom='Mali').first()
if mali:
    regions = Region.objects.filter(pays=mali).count()
    localities = Localite.objects.filter(pays=mali).count()
    print(f'MALI_EXISTS: True')
    print(f'REGIONS: {regions}')
    print(f'LOCALITIES: {localities}')
else:
    print('MALI_EXISTS: False')
