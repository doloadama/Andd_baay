from django.db import migrations, models
import django.db.models.deletion


def link_prevision_to_projet_produit(apps, schema_editor):
    PrevisionRecolte = apps.get_model("baay", "PrevisionRecolte")
    ProjetProduit = apps.get_model("baay", "ProjetProduit")
    for prev in PrevisionRecolte.objects.filter(projet_produit__isnull=True).iterator():
        pp = (
            ProjetProduit.objects.filter(projet_id=prev.projet_id)
            .order_by("date_creation")
            .first()
        )
        if pp:
            prev.projet_produit = pp
            prev.save(update_fields=["projet_produit"])


class Migration(migrations.Migration):

    dependencies = [
        ("baay", "0023_membreferme_role_proprietaire_owner_signal"),
    ]

    operations = [
        migrations.AddField(
            model_name="previsionrecolte",
            name="projet_produit",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="prevision",
                to="baay.projetproduit",
            ),
        ),
        migrations.RunPython(link_prevision_to_projet_produit, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="previsionrecolte",
            name="projet",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="previsions",
                to="baay.projet",
            ),
        ),
        migrations.AlterField(
            model_name="previsionrecolte",
            name="date_prediction",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
