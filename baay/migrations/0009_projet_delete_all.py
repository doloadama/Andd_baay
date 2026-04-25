# Delete all existing projects to prepare for mandatory ferme field

from django.db import migrations


def delete_all_projets(apps, schema_editor):
    Projet = apps.get_model('baay', 'Projet')
    Projet.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0008_ferme_projet_ferme_membreferme'),
    ]

    operations = [
        migrations.RunPython(delete_all_projets, migrations.RunPython.noop),
    ]
