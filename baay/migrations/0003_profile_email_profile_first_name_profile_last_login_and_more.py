# Generated by Django 5.1.4 on 2025-01-09 10:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("baay", "0002_profile_alter_projet_utilisateur_delete_utilisateur"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="email",
            field=models.EmailField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="first_name",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="last_login",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="last_name",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
