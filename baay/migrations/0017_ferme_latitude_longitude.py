from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0016_tache'),
    ]

    operations = [
        migrations.AddField(
            model_name='ferme',
            name='latitude',
            field=models.FloatField(blank=True, help_text='Latitude GPS de la ferme', null=True),
        ),
        migrations.AddField(
            model_name='ferme',
            name='longitude',
            field=models.FloatField(blank=True, help_text='Longitude GPS de la ferme', null=True),
        ),
    ]
