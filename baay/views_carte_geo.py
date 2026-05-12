"""
Vues pour la carte de chaleur des cultures et marketplace géolocalisé.
Pilier 4: Communauté & Géo-Data
"""

import logging
from typing import Optional

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST
from django.core.cache import cache

from baay.models import Pays, Localite, OffreProduit, TransactionMarche, Ferme
from baay.permissions import fermes_accessibles_qs
from baay.services.carte_chaleur_service import (
    generer_geojson_heatmap,
    generer_donnees_heatmap_leaflet,
    obtenir_statistiques_heatmap,
    CULTURES_PRINCIPALES,
    invalider_cache_heatmap,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CARTE DE CHALEUR DES CULTURES
# =============================================================================

@login_required
@require_GET
def carte_heatmap(request: HttpRequest) -> HttpResponse:
    """
    Page principale de la carte de chaleur des cultures.
    Affiche la carte avec filtres.
    """
    # Liste des pays disponibles (ceux qui ont des projets)
    pays_list = Pays.objects.filter(
        localites__projets__isnull=False
    ).distinct().order_by('nom')

    context = {
        'pays_list': pays_list,
        'cultures_list': CULTURES_PRINCIPALES,
        'leaflet_css': 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
        'leaflet_js': 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
        'heatmap_js': 'https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js',
    }

    return render(request, 'carte/heatmap.html', context)


@login_required
@require_GET
def api_geojson_heatmap(request: HttpRequest) -> JsonResponse:
    """
    API: Retourne les données GeoJSON pour la heatmap.
    Filtres: pays, culture_type
    """
    pays_id = request.GET.get('pays')
    culture_type = request.GET.get('culture')

    # Limite de confidentialité: pas de zoom trop précis
    # L'API retourne toujours des données agrégées
    geojson = generer_geojson_heatmap(pays_id, culture_type)

    return JsonResponse(geojson)


@login_required
@require_GET
def api_leaflet_heatmap_data(request: HttpRequest) -> JsonResponse:
    """
    API: Retourne les données au format [lat, lon, intensity] pour Leaflet.heat.
    """
    pays_id = request.GET.get('pays')
    culture_type = request.GET.get('culture')

    data = generer_donnees_heatmap_leaflet(pays_id, culture_type)

    return JsonResponse({'data': data, 'count': len(data)})


@login_required
@require_GET
def api_stats_heatmap(request: HttpRequest) -> JsonResponse:
    """
    API: Retourne les statistiques de la heatmap.
    """
    pays_id = request.GET.get('pays')

    stats = obtenir_statistiques_heatmap(pays_id)

    return JsonResponse(stats)


@login_required
@require_POST
def refresh_heatmap_cache(request: HttpRequest) -> JsonResponse:
    """
    Admin: Force le rafraîchissement du cache heatmap.
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission refusée'}, status=403)

    invalider_cache_heatmap()

    return JsonResponse({'status': 'cache_invalide'})


# =============================================================================
# MARKETPLACE GÉOLOCALISÉ
# =============================================================================

@login_required
@require_GET
def marketplace_liste(request: HttpRequest) -> HttpResponse:
    """
    Liste des offres disponibles sur le marketplace.
    Filtres: produit, localité, qualité, prix max.
    """
    from baay.models import ProduitAgricole

    # Paramètres de filtre
    produit_id = request.GET.get('produit')
    localite_id = request.GET.get('localite')
    qualite = request.GET.get('qualite')
    prix_max = request.GET.get('prix_max')

    # Offres disponibles
    offres = OffreProduit.objects.filter(
        statut='disponible',
    ).select_related('vendeur', 'produit', 'localite_retrait').order_by('-date_creation')

    # Appliquer filtres
    if produit_id:
        offres = offres.filter(produit_id=produit_id)
    if localite_id:
        offres = offres.filter(localite_retrait_id=localite_id)
    if qualite:
        offres = offres.filter(qualite=qualite)
    if prix_max:
        try:
            offres = offres.filter(prix_unitaire__lte=float(prix_max))
        except ValueError:
            pass

    # Fermes de l'utilisateur (pour contact)
    profile = request.user.profile
    mes_fermes = fermes_accessibles_qs(profile)

    context = {
        'offres': offres[:50],  # Pagination manuelle pour MVP
        'produits': ProduitAgricole.objects.filter(offres_marketplace__statut='disponible').distinct(),
        'localites': Localite.objects.filter(offres_retrait__statut='disponible').distinct(),
        'mes_fermes': mes_fermes,
    }

    return render(request, 'marketplace/liste_offres.html', context)


@login_required
@require_GET
def marketplace_detail_offre(request: HttpRequest, offre_id: str) -> HttpResponse:
    """
    Détail d'une offre avec possibilité de contacter le vendeur.
    """
    offre = get_object_or_404(
        OffreProduit.objects.select_related('vendeur', 'produit', 'localite_retrait', 'cree_par'),
        pk=offre_id,
    )

    # Incrémenter le compteur de vues
    offre.nb_vues += 1
    offre.save(update_fields=['nb_vues'])

    # Fermes de l'utilisateur (pour achat potentiel)
    profile = request.user.profile
    mes_fermes = fermes_accessibles_qs(profile)

    # Transactions existantes de l'utilisateur sur cette offre
    mes_transactions = TransactionMarche.objects.filter(
        offre=offre,
        acheteur__in=mes_fermes,
    ).order_by('-date_creation') if mes_fermes else []

    context = {
        'offre': offre,
        'mes_fermes': mes_fermes,
        'mes_transactions': mes_transactions,
        'est_mon_offre': offre.vendeur in mes_fermes,
    }

    return render(request, 'marketplace/detail_offre.html', context)


@login_required
@require_GET
def marketplace_creer_offre_form(request: HttpRequest) -> HttpResponse:
    """
    Formulaire de création d'offre (HTMX partial).
    """
    from baay.models import ProduitAgricole

    profile = request.user.profile
    mes_fermes = fermes_accessibles_qs(profile)

    context = {
        'mes_fermes': mes_fermes,
        'produits': ProduitAgricole.objects.all(),
        'localites': Localite.objects.all(),
    }

    return render(request, 'marketplace/_form_creer_offre.html', context)


@login_required
@require_POST
def marketplace_creer_offre(request: HttpRequest) -> HttpResponse:
    """
    Création d'une offre sur le marketplace.
    """
    from decimal import Decimal
    from datetime import datetime, timedelta
    from baay.models import ProduitAgricole

    profile = request.user.profile

    try:
        vendeur_id = request.POST.get('vendeur')
        produit_id = request.POST.get('produit')
        titre = request.POST.get('titre', '').strip()
        description = request.POST.get('description', '').strip()
        quantite = Decimal(request.POST.get('quantite', 0))
        unite = request.POST.get('unite', 'kg')
        prix = Decimal(request.POST.get('prix', 0))
        qualite = request.POST.get('qualite', 'B')
        localite_id = request.POST.get('localite')
        date_expiration = request.POST.get('date_expiration')
        livraison = request.POST.get('livraison') == 'on'

        # Vérifier permissions
        ferme = get_object_or_404(Ferme, pk=vendeur_id)
        if ferme not in fermes_accessibles_qs(profile):
            return HttpResponse("Permission refusée", status=403)

        produit = get_object_or_404(ProduitAgricole, pk=produit_id)

        # Date d'expiration par défaut: 30 jours
        if date_expiration:
            date_exp = datetime.strptime(date_expiration, '%Y-%m-%d').date()
        else:
            date_exp = (datetime.now() + timedelta(days=30)).date()

        offre = OffreProduit.objects.create(
            vendeur=ferme,
            produit=produit,
            titre_annonce=titre or f"{produit.nom} - {quantite} {unite}",
            description=description,
            quantite_disponible=quantite,
            unite=unite,
            prix_unitaire=prix,
            qualite=qualite,
            localite_retrait_id=localite_id if localite_id else None,
            livraison_possible=livraison,
            date_expiration=date_exp,
            cree_par=profile,
        )

        logger.info("Offre créée: %s par %s", offre.id, profile.user.username)

        return render(request, 'marketplace/_offre_card.html', {'offre': offre})

    except Exception as e:
        logger.exception("Erreur création offre")
        return HttpResponse(f"Erreur: {str(e)}", status=400)


@login_required
@require_POST
def marketplace_initier_transaction(request: HttpRequest, offre_id: str) -> HttpResponse:
    """
    Initie une transaction (réserve) sur une offre.
    """
    profile = request.user.profile
    offre = get_object_or_404(OffreProduit, pk=offre_id, statut='disponible')

    try:
        acheteur_id = request.POST.get('acheteur')
        quantite = float(request.POST.get('quantite', 0))

        acheteur = get_object_or_404(Ferme, pk=acheteur_id)

        # Vérifier permissions
        if acheteur not in fermes_accessibles_qs(profile):
            return HttpResponse("Permission refusée", status=403)

        # Vérifier pas achat de sa propre offre
        if acheteur == offre.vendeur:
            return HttpResponse("Impossible d'acheter sa propre offre", status=400)

        transaction = offre.reserver(acheteur, quantite)
        transaction.cree_par = profile
        transaction.save(update_fields=['cree_par'])

        # Incrémenter compteur contacts
        offre.nb_contacts += 1
        offre.save(update_fields=['nb_contacts'])

        return render(request, 'marketplace/_transaction_card.html', {'transaction': transaction})

    except ValueError as e:
        return HttpResponse(str(e), status=400)
    except Exception as e:
        logger.exception("Erreur transaction")
        return HttpResponse(f"Erreur: {str(e)}", status=400)


@login_required
@require_GET
def marketplace_mes_offres(request: HttpRequest) -> HttpResponse:
    """
    Liste des offres créées par l'utilisateur.
    """
    profile = request.user.profile
    mes_fermes = fermes_accessibles_qs(profile)

    mes_offres = OffreProduit.objects.filter(
        vendeur__in=mes_fermes,
    ).order_by('-date_creation')

    context = {
        'mes_offres': mes_offres,
    }

    return render(request, 'marketplace/mes_offres.html', context)


@login_required
@require_GET
def marketplace_mes_achats(request: HttpRequest) -> HttpResponse:
    """
    Liste des transactions (achats) de l'utilisateur.
    """
    profile = request.user.profile
    mes_fermes = fermes_accessibles_qs(profile)

    mes_achats = TransactionMarche.objects.filter(
        acheteur__in=mes_fermes,
    ).select_related('offre', 'offre__produit', 'offre__vendeur').order_by('-date_creation')

    context = {
        'mes_achats': mes_achats,
    }

    return render(request, 'marketplace/mes_achats.html', context)


@login_required
@require_POST
def marketplace_maj_statut_transaction(request: HttpRequest, transaction_id: str) -> HttpResponse:
    """
    Met à jour le statut d'une transaction (workflow).
    """
    from django.utils import timezone

    profile = request.user.profile
    transaction = get_object_or_404(TransactionMarche, pk=transaction_id)

    # Vérifier permissions (acheteur ou vendeur)
    mes_fermes = fermes_accessibles_qs(profile)
    if transaction.acheteur not in mes_fermes and transaction.offre.vendeur not in mes_fermes:
        return HttpResponse("Permission refusée", status=403)

    nouveau_statut = request.POST.get('statut')
    statuts_valides = [s[0] for s in TransactionMarche.STATUT_CHOICES]

    if nouveau_statut not in statuts_valides:
        return HttpResponse("Statut invalide", status=400)

    transaction.statut = nouveau_statut

    # Mettre à jour dates selon statut
    if nouveau_statut == 'confirme':
        transaction.date_confirmation = timezone.now()
    elif nouveau_statut == 'paye':
        transaction.date_paiement = timezone.now()
        transaction.mode_paiement = request.POST.get('mode_paiement', '')
        transaction.reference_paiement = request.POST.get('reference', '')
    elif nouveau_statut == 'livre':
        transaction.date_livraison = timezone.now()

    transaction.save()

    return render(request, 'marketplace/_transaction_card.html', {'transaction': transaction})
