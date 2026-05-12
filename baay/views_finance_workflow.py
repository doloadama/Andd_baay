"""
Vues HTMX pour le workflow de validation des recettes (Pilier 3 V2).
Gestion des statuts: en_attente -> validee/refusee
"""

import logging
from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from baay.models import Recette, Profile, Ferme
from baay.permissions import fermes_accessibles_qs, role_dans_ferme
from baay.services.roi_simulation_service import (
    creer_simulation,
    comparer_scenarios,
    obtenir_dernieres_simulations,
)

logger = logging.getLogger(__name__)


# =============================================================================
# WORKFLOW VALIDATION RECETTES
# =============================================================================

@login_required
@require_GET
def liste_recettes_validation(request: HttpRequest) -> HttpResponse:
    """
    Liste des recettes en attente de validation pour les fermes gérées.
    Page principale du workflow validation.
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    
    # Récupérer les recettes en attente
    recettes_attente = Recette.objects.filter(
        projet__ferme__in=fermes_qs,
        statut_validation=Recette.STATUT_EN_ATTENTE,
    ).select_related('projet', 'projet__ferme', 'projet_produit').order_by('-date_vente')[:20]
    
    # Statistiques
    stats = {
        'en_attente': Recette.objects.filter(
            projet__ferme__in=fermes_qs,
            statut_validation=Recette.STATUT_EN_ATTENTE
        ).count(),
        'validees_recent': Recette.objects.filter(
            projet__ferme__in=fermes_qs,
            statut_validation=Recette.STATUT_VALIDEE,
            date_validation__isnull=False,
        ).order_by('-date_validation')[:5],
        'refusees_recent': Recette.objects.filter(
            projet__ferme__in=fermes_qs,
            statut_validation=Recette.STATUT_REFUSEE,
        ).order_by('-date_validation')[:5],
    }
    
    context = {
        'recettes_attente': recettes_attente,
        'stats': stats,
    }
    
    return render(request, 'finance/workflow/liste_validation.html', context)


@login_required
@require_GET
def partial_recette_validation(request: HttpRequest, recette_id: str) -> HttpResponse:
    """
    Partial HTMX: Détail d'une recette pour validation.
    Affiché dans modal ou drawer.
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    
    recette = get_object_or_404(
        Recette.objects.select_related('projet', 'projet__ferme', 'projet_produit', 'validee_par'),
        pk=recette_id,
        projet__ferme__in=fermes_qs,
    )
    
    # Vérifier si l'utilisateur peut valider (manager ou propriétaire)
    role = role_dans_ferme(profile, recette.projet.ferme)
    peut_valider = role in ['proprietaire', 'manager']
    
    context = {
        'recette': recette,
        'peut_valider': peut_valider,
    }
    
    return render(request, 'finance/workflow/_modal_validation.html', context)


@login_required
@require_POST
def valider_recette(request: HttpRequest, recette_id: str) -> HttpResponse:
    """
    Action: Valider une recette (manager/propriétaire uniquement).
    HTMX: POST avec commentaire optionnel.
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    
    recette = get_object_or_404(
        Recette,
        pk=recette_id,
        projet__ferme__in=fermes_qs,
        statut_validation=Recette.STATUT_EN_ATTENTE,
    )
    
    # Vérifier permissions
    role = role_dans_ferme(profile, recette.projet.ferme)
    if role not in ['proprietaire', 'manager']:
        return HttpResponse("Permission refusée", status=403)
    
    commentaire = request.POST.get('commentaire', '')
    recette.valider(profile, commentaire)
    
    logger.info("Recette validée: %s par %s", recette_id, profile.user.username)
    
    # Retourne le badge de statut pour mise à jour inline
    return render(request, 'finance/workflow/_badge_statut.html', {'recette': recette})


@login_required
@require_POST
def refuser_recette(request: HttpRequest, recette_id: str) -> HttpResponse:
    """
    Action: Refuser une recette avec motif obligatoire.
    HTMX: POST avec commentaire obligatoire.
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    
    recette = get_object_or_404(
        Recette,
        pk=recette_id,
        projet__ferme__in=fermes_qs,
        statut_validation=Recette.STATUT_EN_ATTENTE,
    )
    
    # Vérifier permissions
    role = role_dans_ferme(profile, recette.projet.ferme)
    if role not in ['proprietaire', 'manager']:
        return HttpResponse("Permission refusée", status=403)
    
    commentaire = request.POST.get('commentaire', '').strip()
    if not commentaire:
        return HttpResponse("Commentaire obligatoire pour un refus", status=400)
    
    recette.refuser(profile, commentaire)
    
    logger.info("Recette refusée: %s par %s", recette_id, profile.user.username)
    
    return render(request, 'finance/workflow/_badge_statut.html', {'recette': recette})


@login_required
@require_GET
def partial_recette_row(request: HttpRequest, recette_id: str) -> HttpResponse:
    """
    Partial HTMX: Ligne de recette avec statut à jour.
    Pour refresh après action validation.
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    
    recette = get_object_or_404(
        Recette.objects.select_related('projet', 'projet__ferme', 'projet_produit'),
        pk=recette_id,
        projet__ferme__in=fermes_qs,
    )
    
    return render(request, 'finance/workflow/_recette_row.html', {'recette': recette})


@login_required
@require_GET
def compteur_recettes_attente(request: HttpRequest) -> HttpResponse:
    """
    Compteur de recettes en attente pour badge notification.
    HTMX: refresh toutes les 5 minutes.
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    
    count = Recette.objects.filter(
        projet__ferme__in=fermes_qs,
        statut_validation=Recette.STATUT_EN_ATTENTE,
    ).count()
    
    if count > 0:
        return HttpResponse(f'<span class="badge bg-danger">{count}</span>')
    return HttpResponse('')


# =============================================================================
# SIMULATION ROI
# =============================================================================

@login_required
@require_GET
def simulateur_roi(request: HttpRequest, projet_id: str) -> HttpResponse:
    """
    Page du simulateur ROI avec sliders interactifs.
    """
    from baay.permissions import projets_accessibles_qs
    
    profile = request.user.profile
    projets_qs = projets_accessibles_qs(profile)
    projet = get_object_or_404(projets_qs, pk=projet_id)
    
    # Scénarios par défaut
    scenarios = comparer_scenarios(projet)
    
    # Dernières simulations
    simulations = obtenir_dernieres_simulations(projet, 5)
    
    context = {
        'projet': projet,
        'scenarios': scenarios,
        'simulations': simulations,
    }
    
    return render(request, 'finance/roi/simulateur.html', context)


@login_required
@require_POST
def creer_simulation_roi(request: HttpRequest, projet_id: str) -> HttpResponse:
    """
    Crée une simulation ROI personnalisée depuis le formulaire.
    HTMX: POST avec valeurs des sliders.
    """
    from decimal import Decimal
    from baay.permissions import projets_accessibles_qs
    
    profile = request.user.profile
    projets_qs = projets_accessibles_qs(profile)
    projet = get_object_or_404(projets_qs, pk=projet_id)
    
    try:
        # Récupérer valeurs du formulaire
        rendement = Decimal(request.POST.get('rendement', 0))
        prix = Decimal(request.POST.get('prix', 0))
        investissement = Decimal(request.POST.get('investissement', 0))
        scenario_type = request.POST.get('scenario_type', 'personnalise')
        nom = request.POST.get('nom_simulation', '')
        description = request.POST.get('description', '')
        
        simulation = creer_simulation(
            projet=projet,
            cree_par=profile,
            scenario_type=scenario_type,
            nom_simulation=nom,
            rendement_kg_ha=rendement,
            prix_fcfa_kg=prix,
            investissement_total=investissement,
            description=description,
        )
        
        logger.info("Simulation ROI créée via formulaire: %s", simulation.id)
        
        # Retourne le nouveau résultat
        return render(request, 'finance/roi/_simulation_result.html', {
            'simulation': simulation,
        })
        
    except Exception as e:
        logger.exception("Erreur création simulation ROI")
        return HttpResponse(f"Erreur: {str(e)}", status=400)


@login_required
@require_GET
def api_comparer_scenarios(request: HttpRequest, projet_id: str) -> JsonResponse:
    """
    API: Retourne les 3 scénarios comparés en JSON.
    Pour mise à jour dynamique des graphiques.
    """
    from baay.permissions import projets_accessibles_qs
    
    profile = request.user.profile
    projets_qs = projets_accessibles_qs(profile)
    projet = get_object_or_404(projets_qs, pk=projet_id)
    
    scenarios = comparer_scenarios(projet)
    
    # Formater pour JSON
    data = {}
    for nom, s in scenarios.items():
        data[nom] = {
            'rendement_kg_ha': float(s['rendement_kg_ha']),
            'prix_fcfa_kg': float(s['prix_fcfa_kg']),
            'investissement': float(s['investissement']),
            'recette_prevue': float(s['recette_prevue']),
            'benefice_prevu': float(s['benefice_prevu']),
            'roi_pct': float(s['roi_pct']),
            'rentabilite': s['rentabilite'],
            'description': s['description'],
        }
    
    return JsonResponse({'scenarios': data, 'projet': projet.nom})


@login_required
@require_POST
def supprimer_simulation(request: HttpRequest, simulation_id: str) -> HttpResponse:
    """
    Supprime une simulation ROI (créateur uniquement).
    HTMX: DELETE action.
    """
    from baay.models import SimulationROI
    
    profile = request.user.profile
    simulation = get_object_or_404(SimulationROI, pk=simulation_id, cree_par=profile)
    
    simulation.delete()
    logger.info("Simulation ROI supprimée: %s", simulation_id)
    
    return HttpResponse("Simulation supprimée", status=200)
