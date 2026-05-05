# Migrations pour Cloudinary — chemins dossier figés avec préfixe "dev/"
# Alignez CLOUDINARY_MEDIA_PREFIX en production (ex. prod) et réimportez/migrez selon votre politique CDN.

import cloudinary.models
from django.db import migrations


def _folder(sub: str) -> str:
    return f"dev/{sub}".strip("/")


class Migration(migrations.Migration):

    dependencies = [
        ("baay", "0035_region_geographie_depense_verrouillage"),
    ]

    operations = [
        migrations.AddField(
            model_name="ferme",
            name="image_couverture",
            field=cloudinary.models.CloudinaryField(
                verbose_name="image_couverture",
                blank=True,
                null=True,
                max_length=255,
                folder=_folder("fermes"),
            ),
        ),
        migrations.AddField(
            model_name="ferme",
            name="image_infrastructure",
            field=cloudinary.models.CloudinaryField(
                verbose_name="image_infrastructure",
                blank=True,
                null=True,
                max_length=255,
                folder=_folder("fermes/infrastructures"),
            ),
        ),
        migrations.AddField(
            model_name="membreferme",
            name="photo_profil",
            field=cloudinary.models.CloudinaryField(
                verbose_name="photo_profil",
                blank=True,
                null=True,
                max_length=255,
                folder=_folder("profils"),
            ),
        ),
        migrations.AlterField(
            model_name="photoproduitagricole",
            name="image",
            field=cloudinary.models.CloudinaryField(
                verbose_name="image",
                max_length=255,
                folder=_folder("produits/catalogue"),
            ),
        ),
        migrations.AlterField(
            model_name="projet",
            name="image_fond",
            field=cloudinary.models.CloudinaryField(
                verbose_name="image_fond",
                blank=True,
                null=True,
                max_length=255,
                folder=_folder("projets/couvertures"),
            ),
        ),
        migrations.AlterField(
            model_name="projetproduit",
            name="image",
            field=cloudinary.models.CloudinaryField(
                verbose_name="image",
                blank=True,
                null=True,
                max_length=255,
                folder=_folder("projets/plants"),
            ),
        ),
        migrations.AddField(
            model_name="recette",
            name="justificatif_facture",
            field=cloudinary.models.CloudinaryField(
                verbose_name="justificatif_facture",
                blank=True,
                null=True,
                max_length=255,
                folder=_folder("finance/recettes"),
                resource_type="auto",
            ),
        ),
        migrations.AddField(
            model_name="depense",
            name="justificatif",
            field=cloudinary.models.CloudinaryField(
                verbose_name="justificatif",
                blank=True,
                null=True,
                max_length=255,
                folder=_folder("finance/depenses"),
                resource_type="auto",
            ),
        ),
        migrations.AddField(
            model_name="investissement",
            name="piece_justificative",
            field=cloudinary.models.CloudinaryField(
                verbose_name="piece_justificative",
                blank=True,
                null=True,
                max_length=255,
                folder=_folder("finance/investissements"),
                resource_type="auto",
            ),
        ),
        migrations.AlterField(
            model_name="message",
            name="piece_jointe",
            field=cloudinary.models.CloudinaryField(
                verbose_name="piece_jointe",
                blank=True,
                null=True,
                max_length=255,
                folder=_folder("messagerie/pieces_jointes"),
                resource_type="auto",
            ),
        ),
    ]
