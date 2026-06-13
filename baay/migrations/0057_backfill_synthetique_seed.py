"""
Rétro-marque les observations PrevisionFeatures issues des données générées
(seed) comme `synthetique=True`, pour qu'elles soient exclues de l'entraînement
ML (anti « réapprentissage du générateur »).

Signature des données seed (créées par `seed_projets_fictifs`) :
  - le projet lié a un nom commençant par "[TEST]", ou
  - la ferme liée s'appelle "Ferme Test ML ..." (Ferme Test ML Calibration).

Réversible : remet `synthetique=False` (sans perte, le champ est purement un drapeau).
"""
from django.db import migrations
from django.db.models import Q


def marquer_seed_synthetique(apps, schema_editor):
    PrevisionFeatures = apps.get_model("baay", "PrevisionFeatures")
    qs = PrevisionFeatures.objects.filter(
        Q(prevision__projet__nom__startswith="[TEST]")
        | Q(prevision__projet__ferme__nom__icontains="Ferme Test ML")
    )
    n = qs.update(synthetique=True)
    print(f"  -> {n} PrevisionFeatures marquées synthetique=True (seed exclu de l'entraînement).")


def demarquer(apps, schema_editor):
    PrevisionFeatures = apps.get_model("baay", "PrevisionFeatures")
    PrevisionFeatures.objects.filter(synthetique=True).update(synthetique=False)


class Migration(migrations.Migration):

    dependencies = [
        ("baay", "0056_previsionfeatures_synthetique"),
    ]

    operations = [
        migrations.RunPython(marquer_seed_synthetique, demarquer),
    ]
