import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'baay.settings')
import django
django.setup()

from baay.models import ProduitAgricole

with open('cultures_result.txt', 'w', encoding='utf-8') as f:
    total = ProduitAgricole.objects.count()
    f.write(f'Total cultures en base: {total}\n\n')
    for p in ProduitAgricole.objects.all().order_by('nom'):
        f.write(f'- {p.nom} ({p.saison or "?"})\n')

print(f'Done - {ProduitAgricole.objects.count()} cultures')
