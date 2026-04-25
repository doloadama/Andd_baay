# Make ferme field mandatory on Projet

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0009_projet_delete_all'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projet',
            name='ferme',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='projets', to='baay.ferme'),
        ),
    ]
