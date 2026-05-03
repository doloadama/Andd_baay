from django.db import migrations, models


def backfill_libelle_from_description(apps, schema_editor):
    Investissement = apps.get_model("baay", "Investissement")
    for inv in Investissement.objects.iterator():
        text = (inv.description or "").strip()
        if text:
            inv.libelle = text.split("\n")[0][:255]
        elif not inv.libelle:
            inv.libelle = "Dépense"
        inv.save(update_fields=["libelle"])


class Migration(migrations.Migration):

    dependencies = [
        ("baay", "0028_investissement_projet_produit_and_pp_budget"),
    ]

    operations = [
        migrations.AddField(
            model_name="investissement",
            name="libelle",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Titre court affiché dans les listes (ex. achat engrais).",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="investissement",
            name="categorie",
            field=models.CharField(
                choices=[
                    ("general", "Général"),
                    ("intrant", "Intrant"),
                    ("main_oeuvre", "Main d'œuvre"),
                    ("transport", "Transport"),
                    ("irrigation", "Irrigation"),
                    ("materiel", "Matériel"),
                ],
                default="general",
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="investissement",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_libelle_from_description, migrations.RunPython.noop),
    ]
