"""Nettoyage des fichiers Cloudinary après suppression des enregistrements."""
from django.db.models.signals import post_delete

from baay.cloudinary_helpers import destroy_cloudinary_value


def _purge_factory(field_names: tuple[str, ...]):
    def _purge(sender, instance, **kwargs):
        for field in field_names:
            destroy_cloudinary_value(getattr(instance, field, None))

    return _purge


_CLOUDINARY_PURGE_TARGETS = (
    ("Ferme", ("image_couverture", "image_infrastructure")),
    ("MembreFerme", ("photo_profil",)),
    ("PhotoProduitAgricole", ("image",)),
    ("Projet", ("image_fond",)),
    ("ProjetProduit", ("image",)),
    ("Recette", ("justificatif_facture",)),
    ("Depense", ("justificatif",)),
    ("Investissement", ("piece_justificative",)),
    ("Message", ("piece_jointe",)),
)


def connect_cloudinary_purge_signals() -> None:
    # Import models here to éviter références circulaires au chargement de l'application.
    from baay import models as baay_models

    lookup = {
        "Ferme": baay_models.Ferme,
        "MembreFerme": baay_models.MembreFerme,
        "PhotoProduitAgricole": baay_models.PhotoProduitAgricole,
        "Projet": baay_models.Projet,
        "ProjetProduit": baay_models.ProjetProduit,
        "Recette": baay_models.Recette,
        "Depense": baay_models.Depense,
        "Investissement": baay_models.Investissement,
        "Message": baay_models.Message,
    }
    for name, fields in _CLOUDINARY_PURGE_TARGETS:
        cls = lookup[name]
        post_delete.connect(
            _purge_factory(fields),
            sender=cls,
            dispatch_uid=f"cloudinary-purge-{name}",
        )


connect_cloudinary_purge_signals()
