# Generated by Django 5.1.4 on 2024-12-12 10:43

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("baay", "0003_remove_utilisateur_type_utilisateur_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="utilisateur",
            name="date_creation",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
