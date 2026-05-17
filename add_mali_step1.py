import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'baay.settings')
django.setup()
from baay.models import Pays
mali, created = Pays.objects.get_or_create(nom='Mali', defaults={'code_iso': 'ML'})
print(f'Mali {"created" if created else "exists"}: {mali.id}')
