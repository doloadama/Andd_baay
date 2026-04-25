# Generated manually

import django.db.models.deletion
from django.db import migrations, models


def delete_all_projets(apps, schema_editor):
    Projet = apps.get_model('baay', 'Projet')
    Projet.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0008_ferme_projet_ferme_membreferme'),
    ]

    operations = [
        migrations.RunPython(delete_all_projets, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='projet',
            name='ferme',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='projets', to='baay.ferme'),
        ),
    ]
