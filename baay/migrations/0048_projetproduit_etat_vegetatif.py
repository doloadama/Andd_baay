from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baay', '0047_add_query_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='projetproduit',
            name='etat_vegetatif',
            field=models.IntegerField(
                blank=True,
                choices=[
                    (1, 'Très mauvais'),
                    (2, 'Mauvais'),
                    (3, 'Normal'),
                    (4, 'Bon'),
                    (5, 'Excellent'),
                ],
                help_text="Observation terrain de l'état de la culture (1=très mauvais, 5=excellent).",
                null=True,
            ),
        ),
    ]
