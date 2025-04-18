# Generated by Django 5.1.4 on 2025-01-22 00:28

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("baay", "0011_projet_localite"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="investissement",
            name="autres_frais",
        ),
        migrations.RemoveField(
            model_name="investissement",
            name="localite",
        ),
        migrations.AddField(
            model_name="investissement",
            name="date_investissement",
            field=models.DateField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="investissement",
            name="description",
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name="produitagricole",
            name="photo",
            field=models.ImageField(
                blank=True, null=True, upload_to="baay/media/produits/"
            ),
        ),
    ]
