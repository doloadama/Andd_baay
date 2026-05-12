"""
Optimisation des requêtes Django - Pilier 5: Excellence Technique

Ce module fournit des utilitaires pour optimiser les requêtes N+1,
mettre en cache les résultats fréquemment accédés, et réduire
la charge sur la base de données.
"""

import logging
from functools import wraps
from typing import Optional, List, Dict, Any, Callable
from decimal import Decimal

from django.db import connection
from django.db.models import QuerySet, Prefetch, Count, Sum, Avg, F
from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType

from baay.models import (
    Projet, ProjetProduit, Ferme, Recette, Investissement,
    OffreProduit, TransactionMarche, Tache, StockProduit,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DECORATEURS DE CACHE
# =============================================================================

def cached_query(timeout: int = 300, key_prefix: str = "query"):
    """
    Décorateur pour cacher le résultat d'une fonction de requête.

    Args:
        timeout: Durée de cache en secondes (défaut: 5 minutes)
        key_prefix: Préfixe pour la clé de cache
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Générer clé de cache unique
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args))}:{hash(str(kwargs))}"

            # Vérifier cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return result

            # Exécuter fonction
            result = func(*args, **kwargs)

            # Mettre en cache
            cache.set(cache_key, result, timeout)
            logger.debug(f"Cache set: {cache_key}")

            return result
        return wrapper
    return decorator


# =============================================================================
# OPTIMISATIONS PROJET
# =============================================================================

def get_projets_optimise(
    user_profile,
    prefetch_budget: bool = True,
    prefetch_taches: bool = True,
    prefetch_produits: bool = True,
) -> QuerySet:
    """
    Récupère les projets avec prefetch optimisé pour éviter N+1.

    Args:
        user_profile: Profil utilisateur pour permissions
        prefetch_budget: Inclure les données budget
        prefetch_taches: Inclure les tâches
        prefetch_produits: Inclure les produits agricoles

    Returns:
        QuerySet optimisé
    """
    from baay.permissions import projets_accessibles_qs

    qs = projets_accessibles_qs(user_profile)

    # Select related pour éviter jointures répétées
    qs = qs.select_related(
        "ferme",
        "ferme__proprietaire",
        "localite",
        "localite__pays",
    )

    # Prefetch related pour collections
    prefetches = []

    if prefetch_produits:
        prefetches.append(
            Prefetch(
                "projet_produits",
                queryset=ProjetProduit.objects.select_related(
                    "produit"
                ).prefetch_related("semis"),
            )
        )

    if prefetch_taches:
        prefetches.append(
            Prefetch(
                "taches",
                queryset=Tache.objects.select_related("assigne_a").order_by("-date_echeance")[:10],
                to_attr="taches_recentes",
            )
        )

    if prefetch_budget:
        prefetches.append("recettes")
        prefetches.append("investissements")

    if prefetches:
        qs = qs.prefetch_related(*prefetches)

    return qs


def get_projet_detail_optimise(projet_id: int) -> Optional[Projet]:
    """
    Récupère un projet avec toutes ses relations prefetch pour le détail.

    Args:
        projet_id: ID du projet

    Returns:
        Projet avec données préchargées ou None
    """
    try:
        return Projet.objects.select_related(
            "ferme",
            "ferme__proprietaire",
            "localite",
            "localite__pays",
        ).prefetch_related(
            Prefetch(
                "projet_produits",
                queryset=ProjetProduit.objects.select_related(
                    "produit",
                    "projet",
                ).prefetch_related(
                    "semis__variete",
                    "semis__engrais_utilises",
                ),
            ),
            Prefetch(
                "taches",
                queryset=Tache.objects.select_related("assigne_a").order_by("date_echeance"),
            ),
            "recettes",
            "investissements",
        ).get(pk=projet_id)
    except Projet.DoesNotExist:
        return None


# =============================================================================
# OPTIMISATIONS FINANCE
# =============================================================================

def get_recettes_avec_totaux(projet_id: Optional[int] = None) -> QuerySet:
    """
    Récupère les recettes avec calculs agrégés en une seule requête.

    Args:
        projet_id: Filtrer par projet (optionnel)

    Returns:
        QuerySet avec annotations de totaux
    """
    qs = Recette.objects.select_related(
        "projet",
        "projet__ferme",
        "projet_produit",
        "projet_produit__produit",
    )

    if projet_id:
        qs = qs.filter(projet_id=projet_id)

    # Annotations pour éviter calculs en Python
    qs = qs.annotate(
        total_projet=Sum("montant", filter=F("projet_id") == F("projet_id")),
    )

    return qs


def get_budget_projet_optimise(projet_id: int) -> Dict[str, Any]:
    """
    Récupère le budget d'un projet avec agrégations SQL.

    Args:
        projet_id: ID du projet

    Returns:
        Dict avec investissements, recettes, solde
    """
    # Une seule requête pour tout le budget
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                (SELECT COALESCE(SUM(montant), 0) FROM baay_investissement WHERE projet_id = %s) as total_investissements,
                (SELECT COALESCE(SUM(montant), 0) FROM baay_recette WHERE projet_id = %s AND statut_validation = 'validee') as total_recettes,
                (SELECT COALESCE(SUM(montant_prevu), 0) FROM baay_recette WHERE projet_id = %s AND statut_validation = 'en_attente') as recettes_attente,
                (SELECT COUNT(*) FROM baay_recette WHERE projet_id = %s AND statut_validation = 'en_attente') as nb_recettes_attente
        """, [projet_id, projet_id, projet_id, projet_id])

        row = cursor.fetchone()

    investissements = Decimal(str(row[0]))
    recettes_validees = Decimal(str(row[1]))
    recettes_attente = Decimal(str(row[2]))
    nb_attente = row[3]

    return {
        "total_investissements": investissements,
        "total_recettes_validees": recettes_validees,
        "recettes_en_attente": recettes_attente,
        "nb_recettes_attente": nb_attente,
        "solde_actuel": recettes_validees - investissements,
        "solde_prevu": (recettes_validees + recettes_attente) - investissements,
    }


# =============================================================================
# OPTIMISATIONS MARKETPLACE
# =============================================================================

def get_offres_optimise(
    produit_id: Optional[int] = None,
    localite_id: Optional[int] = None,
    qualite: Optional[str] = None,
    prix_max: Optional[Decimal] = None,
    limite: int = 50,
) -> QuerySet:
    """
    Récupère les offres avec filtres et prefetch optimisé.

    Args:
        produit_id: Filtrer par produit
        localite_id: Filtrer par localité
        qualite: Filtrer par qualité
        prix_max: Filtrer par prix max
        limite: Limite de résultats

    Returns:
        QuerySet optimisé
    """
    qs = OffreProduit.objects.filter(
        statut="disponible",
    ).select_related(
        "vendeur",
        "produit",
        "localite_retrait",
        "cree_par",
    )

    # Appliquer filtres
    if produit_id:
        qs = qs.filter(produit_id=produit_id)
    if localite_id:
        qs = qs.filter(localite_retrait_id=localite_id)
    if qualite:
        qs = qs.filter(qualite=qualite)
    if prix_max:
        qs = qs.filter(prix_unitaire__lte=prix_max)

    return qs.order_by("-date_creation")[:limite]


@cached_query(timeout=300, key_prefix="marketplace_stats")
def get_marketplace_stats() -> Dict[str, Any]:
    """
    Récupère les statistiques du marketplace (mise en cache 5 min).

    Returns:
        Dict avec statistiques agrégées
    """
    stats = OffreProduit.objects.filter(statut="disponible").aggregate(
        total_offres=Count("id"),
        prix_moyen=Avg("prix_unitaire"),
        quantite_totale=Sum("quantite_disponible"),
    )

    stats_transactions = TransactionMarche.objects.aggregate(
        total_transactions=Count("id"),
        valeur_totale=Sum("prix_total"),
    )

    return {
        "offres_actives": stats["total_offres"] or 0,
        "prix_moyen_unitaire": stats["prix_moyen"] or 0,
        "quantite_totale_disponible": stats["quantite_totale"] or 0,
        "total_transactions": stats_transactions["total_transactions"] or 0,
        "valeur_totale_transactions": stats_transactions["valeur_totale"] or 0,
    }


# =============================================================================
# OPTIMISATIONS STOCK
# =============================================================================

def get_stocks_ferme_optimise(ferme_id: int) -> QuerySet:
    """
    Récupère les stocks d'une ferme avec prefetch produit.

    Args:
        ferme_id: ID de la ferme

    Returns:
        QuerySet optimisé
    """
    return StockProduit.objects.filter(
        ferme_id=ferme_id,
    ).select_related(
        "produit",
        "projet_produit",
        "projet_produit__projet",
    ).order_by("-quantite_actuelle")


# =============================================================================
# UTILITAIRES DE DEBUG
# =============================================================================

def log_queries(func: Callable) -> Callable:
    """
    Décorateur pour logger les requêtes SQL exécutées par une fonction.
    Utile pour le debugging des problèmes N+1.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        from django.db import reset_queries, connection

        reset_queries()

        result = func(*args, **kwargs)

        queries = connection.queries
        total_time = sum(float(q["time"]) for q in queries)

        logger.info(f"{func.__name__}: {len(queries)} requêtes en {total_time:.3f}s")

        for i, query in enumerate(queries[:5], 1):  # Log les 5 premières
            logger.debug(f"  Query {i}: {query['sql'][:100]}...")

        if len(queries) > 20:
            logger.warning(f"{func.__name__}: Nombre élevé de requêtes ({len(queries)})")

        return result
    return wrapper


def detect_nplus1(qs: QuerySet, threshold: int = 10) -> List[str]:
    """
    Détecte les potentiels problèmes N+1 dans un QuerySet.

    Args:
        qs: QuerySet à analyser
        threshold: Seuil d'alerte

    Returns:
        Liste des warnings
    """
    warnings = []

    # Vérifier les relations manquantes
    if hasattr(qs, 'query'):
        query = qs.query

        # Vérifier select_related
        if not query.select_related:
            warnings.append("Pas de select_related - risque N+1 sur relations FK")

        # Vérifier prefetch_related
        if not query.prefetch_related:
            warnings.append("Pas de prefetch_related - risque N+1 sur relations M2M/Reverse")

    return warnings


# =============================================================================
# EXEMPLES D'UTILISATION
# =============================================================================

"""
# EXEMPLE 1: Remplacer une vue lente

# AVANT (N+1 problem):
def projet_detail_lent(request, pk):
    projet = Projet.objects.get(pk=pk)
    # N requêtes pour les produits
    for pp in projet.projet_produits.all():
        print(pp.produit.nom)  # N requêtes !

# APRÈS (optimisé):
def projet_detail_rapide(request, pk):
    projet = get_projet_detail_optimise(pk)
    # 1 requête seule
    for pp in projet.projet_produits.all():
        print(pp.produit.nom)  # Déjà chargé !


# EXEMPLE 2: Utiliser le cache

@cached_query(timeout=600)  # 10 minutes
def get_stats_dashboard():
    # Cette requête lourde est cachée
    return calculer_statistiques_complexes()


# EXEMPLE 3: Budget en une requête

def dashboard_finance(request, projet_id):
    # Une seule requête SQL pour tout le budget
    budget = get_budget_projet_optimise(projet_id)
    return render(request, "finance/dashboard.html", budget)
"""
