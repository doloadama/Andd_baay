from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0010_projet_ferme_required'),
    ]

    operations = [
        migrations.AddField(
            model_name='membreferme',
            name='peut_gerer_membres',
            field=models.BooleanField(default=False),
        ),
    ]
