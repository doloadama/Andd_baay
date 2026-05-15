"""
Services métier du module d'inventaire (intrants et récoltes).

Gère les mouvements de stock, les alertes de seuil et le lien automatique
avec les investissements de type 'intrant'.
"""

from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import Sum, F, DecimalField

from baay.models import (
    Ferme,
    Investissement,
    MouvementStock,
    Profile,
    StockIntrant,
    StockRecolte,
)


def _normaliser_nom(nom: str) -> str:
    """Normalise un nom d'intrant pour le matching fuzzy."""
    import unicodedata
    nettoye = unicodedata.normalize('NFKD', nom).encode('ASCII', 'ignore').decode('ASCII')
    return nettoye.lower().strip()


@transaction.atomic
def ajuster_stock_intrant(
    stock_id: str,
    delta: Decimal,
    raison: str,
    utilisateur: Optional[Profile] = None,
) -> StockIntrant:
    """
    Ajuste la quantité d'un intrant et crée un MouvementStock.

    :param stock_id: UUID du StockIntrant.
    :param delta: Quantité à ajouter (positif = entrée, négatif = sortie).
    :param raison: Description du mouvement.
    :param utilisateur: Auteur du mouvement (optionnel).
    :return: Instance StockIntrant mise à jour.
    :raises StockIntrant.DoesNotExist: Si le stock n'existe pas.
    """
    stock = StockIntrant.objects.select_for_update().get(pk=stock_id)
    ancienne_qte = stock.quantite
    stock.quantite = max(Decimal('0.00'), stock.quantite + delta)
    stock.save(update_fields=["quantite", "date_modification"])

    MouvementStock.objects.create(
        ferme=stock.ferme,
        type=MouvementStock.TYPE_ENTREE if delta > 0 else MouvementStock.TYPE_SORTIE,
        stock_intrant=stock,
        quantite=abs(delta),
        raison=raison,
        utilisateur=utilisateur,
    )
    return stock


@transaction.atomic
def ajuster_stock_recolte(
    stock_id: str,
    delta: Decimal,
    raison: str,
    utilisateur: Optional[Profile] = None,
) -> StockRecolte:
    """
    Ajuste la quantité d'une récolte et crée un MouvementStock.

    :param stock_id: UUID du StockRecolte.
    :param delta: Quantité à ajouter (positif = entrée, négatif = sortie).
    :param raison: Description du mouvement.
    :param utilisateur: Auteur du mouvement (optionnel).
    :return: Instance StockRecolte mise à jour.
    :raises StockRecolte.DoesNotExist: Si le stock n'existe pas.
    """
    stock = StockRecolte.objects.select_for_update().get(pk=stock_id)
    stock.quantite = max(Decimal('0.00'), stock.quantite + delta)
    stock.save(update_fields=["quantite", "date_modification"])

    MouvementStock.objects.create(
        ferme=stock.ferme,
        type=MouvementStock.TYPE_ENTREE if delta > 0 else MouvementStock.TYPE_SORTIE,
        stock_recolte=stock,
        quantite=abs(delta),
        raison=raison,
        utilisateur=utilisateur,
    )
    return stock


def stocks_en_alerte(ferme: Ferme) -> list[StockIntrant]:
    """
    Retourne les intrants dont la quantité est inférieure au seuil d'alerte.
    """
    return list(
        StockIntrant.objects.filter(
            ferme=ferme,
            quantite__lt=F("seuil_alerte"),
        ).order_by("nom")
    )


def volume_total_recoltes(ferme: Ferme) -> Decimal:
    """
    Retourne la somme totale des quantités de récoltes (en kg, conversion approximative).
    """
    from django.db.models import Case, Value, When

    total = StockRecolte.objects.filter(ferme=ferme).aggregate(
        total=Sum(
            Case(
                When(unite=StockRecolte.UNITE_TONNES, then=F("quantite") * 1000),
                default=F("quantite"),
                output_field=DecimalField(),
            )
        )
    )["total"]
    return total or Decimal("0.00")


def historique_mouvements(ferme: Ferme, limit: int = 50) -> list[MouvementStock]:
    """
    Retourne les derniers mouvements de stock d'une ferme.
    """
    return list(
        MouvementStock.objects.filter(ferme=ferme)
        .select_related("stock_intrant", "stock_recolte", "utilisateur__user")
        .order_by("-date_mouvement")[:limit]
    )


@transaction.atomic
def lier_investissement_a_stock(investissement: Investissement) -> Optional[MouvementStock]:
    """
    Lorsqu'un investissement de type 'intrant' est validé,
    incrémente automatiquement le stock correspondant (match par nom normalisé).

    :param investissement: L'instance Investissement créée ou mise à jour.
    :return: Le MouvementStock créé, ou None si non applicable.
    """
    if investissement.categorie != "intrant":
        return None

    ferme = investissement.projet.ferme
    nom_normalise = _normaliser_nom(investissement.libelle)

    # Recherche d'un StockIntrant existant par nom normalisé
    stock = None
    for candidat in StockIntrant.objects.filter(ferme=ferme):
        if _normaliser_nom(candidat.nom) == nom_normalise:
            stock = candidat
            break

    if stock is None:
        # Création d'un nouveau stock d'intrant
        stock = StockIntrant.objects.create(
            ferme=ferme,
            nom=investissement.libelle.strip() or "Intrant",
            categorie=StockIntrant.CATEGORIE_AUTRE,
            quantite=Decimal("0.00"),
            unite=StockIntrant.UNITE_KG,
            seuil_alerte=Decimal("10.00"),
        )

    # Le montant de l'investissement ne donne pas directement une quantité en kg :
    # on utilise une heuristique simple (1 unité = 1 kg si pas d'info).
    # Dans un cas réel, cela nécessiterait un mapping produit → unité/prix.
    quantite_estimee = Decimal("1.00")  # Valeur par défaut conservatrice

    stock.quantite += quantite_estimee
    stock.save(update_fields=["quantite", "date_modification"])

    mouvement = MouvementStock.objects.create(
        ferme=ferme,
        type=MouvementStock.TYPE_ENTREE,
        stock_intrant=stock,
        quantite=quantite_estimee,
        raison=f"Achat lié à l'investissement {investissement.libelle}",
        investissement=investissement,
    )
    return mouvement
