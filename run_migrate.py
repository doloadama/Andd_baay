import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Andd_Baayi.settings')

import django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'baay_ferme' AND column_name = 'code_acces'
    """)
    result = cursor.fetchall()

with open('check_result.txt', 'w') as f:
    f.write(f"code_acces column exists: {bool(result)}\n")
    f.write(f"Result: {result}\n")

    if not result:
        f.write("Column missing - running migration SQL...\n")
        try:
            cursor.execute("ALTER TABLE baay_ferme ADD COLUMN code_acces VARCHAR(12) UNIQUE")
            f.write("ALTER TABLE done.\n")
        except Exception as e:
            f.write(f"ALTER TABLE error: {e}\n")

        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS baay_demandeaccesferme (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    code VARCHAR(12) NOT NULL,
                    statut VARCHAR(20) NOT NULL DEFAULT 'en_attente',
                    date_demande TIMESTAMP NOT NULL DEFAULT NOW(),
                    date_traitement TIMESTAMP NULL,
                    ferme_id UUID NOT NULL REFERENCES baay_ferme(id) ON DELETE CASCADE,
                    utilisateur_id UUID NOT NULL REFERENCES baay_profile(id) ON DELETE CASCADE,
                    UNIQUE (ferme_id, utilisateur_id, statut)
                )
            """)
            f.write("CREATE TABLE done.\n")
        except Exception as e:
            f.write(f"CREATE TABLE error: {e}\n")
    else:
        f.write("Column already exists - no action needed.\n")

print("Done. See check_result.txt")
