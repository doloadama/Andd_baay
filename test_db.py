import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'baay.settings')

import django
django.setup()

from baay.models import Pays, Region, Localite

if __name__ == '__main__':
    print("Checking database...")
    sys.stdout.flush()

    # Check if Mali exists
    mali_count = Pays.objects.filter(nom='Mali').count()
    print(f"Mali count: {mali_count}")
    sys.stdout.flush()

    # Check regions count
    regions_count = Region.objects.count()
    print(f"Total regions: {regions_count}")
    sys.stdout.flush()

    # Check localities count
    localities_count = Localite.objects.count()
    print(f"Total localities: {localities_count}")
    sys.stdout.flush()

    print("Done!")
