from django.db import migrations, models


def normalize_proprietaire_role(apps, schema_editor):
    """Convertit toute ligne MembreFerme avec role='proprietaire' en 'manager'.
    Le vrai propriétaire est tracé via Ferme.proprietaire et n'est jamais
    censé apparaître dans MembreFerme.
    """
    MembreFerme = apps.get_model('baay', 'MembreFerme')
    MembreFerme.objects.filter(role='proprietaire').update(role='manager')


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0014_alter_demandeaccesferme_unique_constraint'),
    ]

    operations = [
        migrations.RunPython(normalize_proprietaire_role, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='membreferme',
            name='role',
            field=models.CharField(
                choices=[
                    ('manager', 'Manager'),
                    ('technicien', 'Technicien'),
                    ('ouvrier', 'Ouvrier'),
                ],
                default='ouvrier',
                max_length=20,
            ),
        ),
    ]
