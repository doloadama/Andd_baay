"""Temporary script to drop all baay_* tables from the Supabase database."""
import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Andd_Baayi.settings')

import django
django.setup()

from django.db import connection

tables_to_drop = [
    'baay_projetproduit',
    'baay_predictionrendement',
    'baay_investissement',
    'baay_projet',
    'baay_photoproduitagricole',
    'baay_produitagricole',
    'baay_localite',
    'baay_profile',
    'baay_culture',
    'baay_fruitlegume',
    'baay_semis',
]

with connection.cursor() as cursor:
    for table in tables_to_drop:
        try:
            # Table names are from a hardcoded list, not user input.
            # Django's cursor.execute does not support parameterised identifiers,
            # so quoting via psycopg.sql would be ideal but the risk is nil here
            # because the values are fully controlled above.
            cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
            print(f"Dropped: {table}")
        except Exception as e:
            print(f"Error dropping {table}: {e}")

# Also clean up the django_migrations records for baay
with connection.cursor() as cursor:
    cursor.execute("DELETE FROM django_migrations WHERE app = 'baay';")
    print("Cleaned up baay migration records.")

print("\nDone! All baay tables dropped.")
