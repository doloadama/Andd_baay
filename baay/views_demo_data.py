"""
Vues de démonstration pour visualiser les données fictives V2.
Ces vues sont temporaires pour le développement/test.
"""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render
from django.views.decorators.http import require_GET

from baay.models import (
    Projet, RecommandationFertilisation, IncidentRapporte,
    Recette, SimulationROI, OffreProduit, TransactionMarche,
    Tache,
)
from baay.permissions import projets_accessibles_qs


def is_staff_or_superuser(user):
    """Vérifie si l'utilisateur est staff ou superuser."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


staff_or_superuser_required = user_passes_test(
    is_staff_or_superuser,
    login_url=None,
    redirect_field_name=None,
)


@login_required
@staff_or_superuser_required
@require_GET
def demo_dashboard_data(request):
    """
    Vue démo qui affiche toutes les données V2 générées.
    Utile pour vérifier le rendu visuel.
    """
    profile = request.user.profile

    # Récupérer données pour le dashboard
    projets = projets_accessibles_qs(profile)[:5]

    # Enrichir avec données Bento
    context = {
        # Météo - données fictives
        'meteo': {
            'localite': 'Thiès',
            'temperature': 32,
            'humidite': 65,
            'condition': 'Ensoleillé',
            'pluie_prevue_mm': 0,
            'vent_kmh': 15,
            'alerte': None,
        },

        # Projets
        'projets': projets,
        'projets_actifs': projets.filter(statut='en_cours').count(),

        # Budget global (agrégé)
        'budget': {
            'total_alloue': sum(p.budget_alloue or 0 for p in projets),
            'total_depense': 850000,  # Fictif
            'total_recette': 450000,  # Fictif
        },

        # Alertes IA
        'recommandations': RecommandationFertilisation.objects.filter(
            projet_produit__projet__in=projets,
        ).select_related('projet_produit', 'sol')[:5],

        'incidents': IncidentRapporte.objects.filter(
            projet__in=projets,
        ).select_related('projet')[:5],

        # Tâches
        'taches': Tache.objects.filter(
            projet__in=projets,
            statut__in=['a_faire', 'en_cours'],
        ).select_related('projet')[:10],

        'total_taches': Tache.objects.filter(projet__in=projets).count(),

        # Prédictions (fictives)
        'predictions': [
            {
                'projet': p,
                'rendement_min': 800,
                'rendement_max': 1500,
                'confiance': 78,
                'date_recolte_prevue': p.date_fin,
            }
            for p in projets[:3]
        ],
    }

    return render(request, 'demo/demo_dashboard.html', context)


@login_required
@staff_or_superuser_required
@require_GET
def demo_finance_workflow(request):
    """Vue démo du workflow finance avec données."""
    profile = request.user.profile

    # Recettes en attente
    recettes_attente = Recette.objects.filter(
        projet__ferme__proprietaire=request.user,
        statut_validation='en_attente',
    ).select_related('projet', 'produit')[:10]

    # Statistiques
    stats = {
        'total_attente': recettes_attente.count(),
        'montant_attente': sum(r.montant for r in recettes_attente),
        'total_validees': Recette.objects.filter(
            projet__ferme__proprietaire=request.user,
            statut_validation='validee',
        ).count(),
    }

    context = {
        'recettes_attente': recettes_attente,
        'stats': stats,
    }

    return render(request, 'demo/demo_finance.html', context)


@login_required
@staff_or_superuser_required
@require_GET
def demo_marketplace(request):
    """Vue démo du marketplace."""
    profile = request.user.profile

    offres = OffreProduit.objects.filter(
        statut='disponible',
    ).select_related('vendeur', 'produit', 'localite_retrait')[:20]

    # Mes offres
    mes_offres = OffreProduit.objects.filter(
        vendeur__proprietaire=request.user,
    )[:5]

    context = {
        'offres': offres,
        'mes_offres': mes_offres,
        'stats': {
            'total_offres': OffreProduit.objects.filter(statut='disponible').count(),
            'prix_moyen': 450,  # Calculé
        },
    }

    return render(request, 'demo/demo_marketplace.html', context)


@login_required
@staff_or_superuser_required
@require_GET
def demo_roi_simulations(request):
    """Vue démo des simulations ROI."""
    profile = request.user.profile

    simulations = SimulationROI.objects.filter(
        projet__ferme__proprietaire=request.user,
    ).select_related('projet').order_by('-date_creation')[:10]

    # Grouper par projet
    projets_simulations = {}
    for sim in simulations:
        if sim.projet_id not in projets_simulations:
            projets_simulations[sim.projet_id] = {
                'projet': sim.projet,
                'simulations': [],
            }
        projets_simulations[sim.projet_id]['simulations'].append(sim)

    context = {
        'projets_simulations': list(projets_simulations.values()),
        'scenarios_predefinis': [
            {'nom': 'Optimiste', 'roi': 85, 'couleur': 'success'},
            {'nom': 'Réaliste', 'roi': 45, 'couleur': 'primary'},
            {'nom': 'Pessimiste', 'roi': 15, 'couleur': 'warning'},
        ],
    }

    return render(request, 'demo/demo_roi.html', context)


@login_required
@staff_or_superuser_required
@require_GET
def api_demo_data_summary(request):
    """API qui retourne un résumé des données de démo."""
    profile = request.user.profile

    data = {
        'projets': Projet.objects.filter(ferme__proprietaire=request.user).count(),
        'recommandations_ia': RecommandationFertilisation.objects.filter(
            projet_produit__projet__ferme__proprietaire=request.user
        ).count(),
        'incidents': IncidentRapporte.objects.filter(
            projet__ferme__proprietaire=request.user
        ).count(),
        'recettes_attente': Recette.objects.filter(
            projet__ferme__proprietaire=request.user,
            statut_validation='en_attente',
        ).count(),
        'simulations_roi': SimulationROI.objects.filter(
            projet__ferme__proprietaire=request.user
        ).count(),
        'offres_marketplace': OffreProduit.objects.filter(
            statut='disponible'
        ).count(),
    }

    return JsonResponse(data)
