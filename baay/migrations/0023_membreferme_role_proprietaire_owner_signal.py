from django.db import migrations, models


def backfill_proprietaire_membres(apps, schema_editor):
    Ferme = apps.get_model("baay", "Ferme")
    MembreFerme = apps.get_model("baay", "MembreFerme")
    for ferme in Ferme.objects.iterator():
        membre, created = MembreFerme.objects.get_or_create(
            ferme=ferme,
            utilisateur_id=ferme.proprietaire_id,
            defaults={"role": "proprietaire", "peut_gerer_membres": True},
        )
        if not created and membre.role != "proprietaire":
            membre.role = "proprietaire"
            membre.peut_gerer_membres = True
            membre.save(update_fields=["role", "peut_gerer_membres"])


class Migration(migrations.Migration):

    dependencies = [
        ("baay", "0022_participation_conversation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="membreferme",
            name="role",
            field=models.CharField(
                choices=[
                    ("proprietaire", "Propriétaire"),
                    ("manager", "Manager"),
                    ("technicien", "Technicien"),
                    ("ouvrier", "Ouvrier"),
                ],
                default="ouvrier",
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_proprietaire_membres, migrations.RunPython.noop),
    ]
