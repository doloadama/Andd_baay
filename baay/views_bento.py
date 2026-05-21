"""
Vues HTMX pour le Dashboard Bento d'Andd Baay V2.
Cartes indépendantes avec mises à jour partielles.
"""

import logging
from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods

from baay.models import Ferme, HistoriqueSol, IncidentRapporte, Projet, RecommandationFertilisation
from baay.permissions import fermes_accessibles_qs, projets_accessibles_qs
from baay.services import get_weather_data, calculer_kpis_financiers_projet
from baay.services.fertilisation_service import obtenir_derniere_recommandation
from baay.services.rag_service import RAGService

logger = logging.getLogger(__name__)


# =============================================================================
# DASHBOARD BENTO - PAGE PRINCIPALE (Baay Pro)
# =============================================================================

@login_required
def bento_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Page principale du dashboard Bento (Baay Pro).
    Les ouvriers sans rôle supérieur sont automatiquement redirigés vers Baay Simple,
    sauf s'ils ont explicitement demandé la vue complète.
    """
    from django.shortcuts import redirect as dj_redirect
    from baay.permissions import role_dans_ferme, ROLE_OUVRIER

    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)

    # Ferme active (session ou première ferme)
    ferme_id = request.session.get('ferme_active_id')
    ferme_active = None
    if ferme_id:
        ferme_active = fermes_qs.filter(pk=ferme_id).first()
    if not ferme_active and fermes_qs.exists():
        ferme_active = fermes_qs.first()
        if ferme_active:
            request.session['ferme_active_id'] = str(ferme_active.id)

    # Redirection automatique si l'utilisateur n'a que le rôle ouvrier
    # Le paramètre ?vue_complete=1 ou le flag session permettent de passer outre.
    forcer_vue_complete = (
        request.GET.get('vue_complete') == '1'
        or request.session.get('vue_complete_forcee', False)
    )
    if request.GET.get('vue_complete') == '1':
        request.session['vue_complete_forcee'] = True

    if not forcer_vue_complete and ferme_active:
        role = role_dans_ferme(profile, ferme_active)
        # Vérifie si l'utilisateur n'a que le rôle ouvrier dans TOUTES ses fermes
        tous_roles = set()
        for f in fermes_qs:
            r = role_dans_ferme(profile, f)
            if r:
                tous_roles.add(r)
        if tous_roles and tous_roles.issubset({ROLE_OUVRIER}):
            return dj_redirect('dashboard:bento_dashboard_simple')

    context = {
        'fermes': fermes_qs,
        'ferme_active': ferme_active,
        'has_multiple_fermes': fermes_qs.count() > 1,
    }

    return render(request, 'dashboard/bento_base.html', context)



@login_required
@require_http_methods(['POST'])
def set_ferme_active(request: HttpRequest, ferme_id: str) -> HttpResponse:
    """
    Change la ferme active et déclenche mise à jour de toutes les cartes.
    HTMX: POST avec hx-target sur container principal.
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    
    ferme = get_object_or_404(fermes_qs, pk=ferme_id)
    request.session['ferme_active_id'] = str(ferme.id)
    
    # Retourne confirmation + trigger pour refresh autres cartes
    response = HttpResponse(
        f"<span class='text-success'>✓ Ferme active: {ferme.nom}</span>"
    )
    response['HX-Trigger'] = 'ferme-changed'
    return response


# =============================================================================
# DASHBOARD BENTO SIMPLE - Baay Simple (Ouvriers & travailleurs terrain)
# =============================================================================

@login_required
def bento_dashboard_simple(request: HttpRequest) -> HttpResponse:
    """
    Dashboard simplifié pour les ouvriers et travailleurs de terrain.
    Interface visuelle, grands éléments tactiles, mode hors-ligne.
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)

    ferme_id = request.session.get('ferme_active_id')
    ferme_active = None
    if ferme_id:
        ferme_active = fermes_qs.filter(pk=ferme_id).first()
    if not ferme_active and fermes_qs.exists():
        ferme_active = fermes_qs.first()

    context = {
        'fermes': fermes_qs,
        'ferme_active': ferme_active,
        'has_multiple_fermes': fermes_qs.count() > 1,
    }
    return render(request, 'dashboard/bento_base_simple.html', context)


@login_required
@require_http_methods(['POST'])
def tache_terminer_simple(request: HttpRequest, tache_id: str) -> HttpResponse:
    """
    Endpoint HTMX one-tap : marque une tâche comme terminée.
    Accessible uniquement à l'assigné de la tâche.
    """
    from baay.models import Tache
    from django.utils import timezone as tz

    profile = request.user.profile
    tache = get_object_or_404(Tache, pk=tache_id, assigne_a=profile)

    if tache.statut not in ('terminee', 'annulee'):
        tache.statut = 'terminee'
        tache.date_terminee = tz.now()
        tache.save(update_fields=['statut', 'date_terminee', 'date_modification'])

    # Renvoie le fragment de la carte mise à jour
    return bento_card_taches_simple(request)




# =============================================================================
# CARTE BENTO: MÉTÉO
# =============================================================================

@login_required
@require_GET
def bento_card_meteo(request: HttpRequest) -> HttpResponse:
    """
    Carte Bento: Météo de la ferme active.
    hx-get url, hx-trigger="load, every 30m".
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    
    ferme_id = request.session.get('ferme_active_id')
    ferme = fermes_qs.filter(pk=ferme_id).first() if ferme_id else fermes_qs.first()
    
    weather_data = None
    error = None
    
    if ferme and ferme.latitude and ferme.longitude:
        result = get_weather_data(str(ferme.id))
        if result.get('ok'):
            weather_data = result.get('data')
        else:
            error = result.get('error', 'données_météo_indisponibles')
    elif ferme:
        error = 'coords_manquantes'
    
    context = {
        'weather': weather_data,
        'ferme': ferme,
        'error': error,
    }
    
    return render(request, 'dashboard/bento_cards/_card_meteo.html', context)


# =============================================================================
# CARTE BENTO: PROJETS / PROGRESSION
# =============================================================================

@login_required
@require_GET
def bento_card_projets(request: HttpRequest) -> HttpResponse:
    """
    Carte Bento: Liste des projets en cours avec progression.
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    projets_qs = projets_accessibles_qs(profile).filter(
        ferme__in=fermes_qs,
        statut__in=['en_cours', 'en_pause']
    ).select_related('ferme', 'culture').order_by('-date_lancement')[:5]
    
    # Enrichir avec données avancement
    projets_data = []
    for projet in projets_qs:
        prog = projet.avancement_pour_api()
        projets_data.append({
            'projet': projet,
            'taux_avancement': prog['taux_avancement'],
            'source': prog['taux_avancement_source'],
            'tasks_done': prog.get('tasks_done', 0),
            'tasks_total': prog.get('tasks_total', 0),
        })
    
    context = {
        'projets': projets_data,
        'count': len(projets_data),
    }
    
    return render(request, 'dashboard/bento_cards/_card_projets.html', context)


@login_required
@require_GET
def bento_projet_detail_card(request: HttpRequest, projet_id: str) -> HttpResponse:
    """
    Détail d'un projet pour affichage dans carte Bento.
    HTMX: clic sur projet met à jour carte budget/voisine.
    """
    profile = request.user.profile
    projets_qs = projets_accessibles_qs(profile)
    projet = get_object_or_404(projets_qs, pk=projet_id)
    
    # KPIs financiers
    kpis = calculer_kpis_financiers_projet(projet.id)
    
    context = {
        'projet': projet,
        'kpis': kpis,
    }
    
    # Déclencher mise à jour carte budget
    response = render(request, 'dashboard/partials/_projet_detail_for_card.html', context)
    response['HX-Trigger-After-Settle'] = f'{{"update-budget": {{"projet_id": "{projet_id}"}}}}'
    return response


# =============================================================================
# CARTE BENTO: BUDGET / FINANCES
# =============================================================================

@login_required
@require_GET
def bento_card_budget(request: HttpRequest, projet_id: str = None) -> HttpResponse:
    """
    Carte Bento: Budget et finances.
    Si projet_id fourni (via HTMX trigger), affiche détail ce projet.
    Sinon affiche agrégation sur tous les projets accessibles.
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    projets_qs = projets_accessibles_qs(profile).filter(ferme__in=fermes_qs)
    
    # Calculs financiers
    total_budget = 0
    total_depenses = 0
    projets_avec_budget = 0
    
    if projet_id:
        # Vue projet spécifique
        projet = get_object_or_404(projets_qs, pk=projet_id)
        kpis = calculer_kpis_financiers_projet(projet.id)
        total_budget = projet.budget_alloue or 0
        total_depenses = kpis['total_couts']
        projets_avec_budget = 1 if projet.budget_alloue else 0
        
        context = {
            'mode': 'projet',
            'projet': projet,
            'budget_alloue': total_budget,
            'depenses': total_depenses,
            'restant': max(0, total_budget - total_depenses),
            'roi_pct': kpis.get('roi_pct'),
            'taux_utilisation': (total_depenses / total_budget * 100) if total_budget else 0,
        }
    else:
        # Vue agrégée
        for projet in projets_qs:
            if projet.budget_alloue:
                total_budget += projet.budget_alloue
                projets_avec_budget += 1
        
        # Calcul rapide dépenses
        from baay.services import calculer_kpis_financiers_par_projet
        kpis_par_projet = calculer_kpis_financiers_par_projet(
            list(projets_qs.values_list('id', flat=True))
        )
        for p_kpis in kpis_par_projet.values():
            total_depenses += p_kpis['total_couts']
        
        context = {
            'mode': 'agregate',
            'projets_count': projets_qs.count(),
            'projets_avec_budget': projets_avec_budget,
            'budget_total': total_budget,
            'depenses_total': total_depenses,
            'restant_total': max(0, total_budget - total_depenses),
        }
    
    return render(request, 'dashboard/bento_cards/_card_budget.html', context)


# =============================================================================
# CARTE BENTO: ALERTES IA (RECOMMANDATIONS)
# =============================================================================

@login_required
@require_GET
def bento_card_alertes_ia(request: HttpRequest) -> HttpResponse:
    """
    Carte Bento: Alertes et recommandations IA.
    - Dernières recommandations fertilisation
    - Incidents non traités
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    
    # Recommandations récentes non vues
    recommandations = RecommandationFertilisation.objects.filter(
        historique_sol__ferme__in=fermes_qs,
        vue_par_utilisateur__isnull=True,
    ).select_related('historique_sol', 'culture_cible').order_by('-date_creation')[:3]
    
    # Incidents non résolus
    incidents = IncidentRapporte.objects.filter(
        ferme__in=fermes_qs,
        statut__in=['signale', 'en_cours'],
    ).select_related('ferme', 'signale_par').order_by('-date_signalement')[:3]
    
    context = {
        'recommandations': recommandations,
        'incidents': incidents,
        'total_alertes': len(recommandations) + len(incidents),
    }
    
    return render(request, 'dashboard/bento_cards/_card_alertes_ia.html', context)


@login_required
@require_GET
def marquer_recommandation_vue(request: HttpRequest, recommandation_id: str) -> HttpResponse:
    """
    Marque une recommandation comme vue (dismiss alert).
    HTMX: POST pour marquer comme vue.
    """
    from django.utils import timezone
    
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    
    reco = get_object_or_404(
        RecommandationFertilisation,
        pk=recommandation_id,
        historique_sol__ferme__in=fermes_qs,
    )
    reco.vue_par_utilisateur = timezone.now()
    reco.save(update_fields=['vue_par_utilisateur'])
    
    # Retourne updated card
    return bento_card_alertes_ia(request)


# =============================================================================
# CARTE BENTO: TÂCHES PRIORITAIRES
# =============================================================================

@login_required
@require_GET
def bento_card_taches(request: HttpRequest) -> HttpResponse:
    """
    Carte Bento: Tâches prioritaires (haute/urgente) à faire/en cours.
    """
    from baay.models import Tache
    
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    
    taches = Tache.objects.filter(
        ferme__in=fermes_qs,
        statut__in=['a_faire', 'en_cours'],
        priorite__in=['haute', 'urgente'],
    ).select_related('ferme', 'assigne_a').order_by('date_echeance')[:5]
    
    # Tâches en retard
    from django.utils import timezone
    today = timezone.localdate()
    taches_retard = [t for t in taches if t.date_echeance and t.date_echeance < today]
    
    context = {
        'taches': taches,
        'taches_retard_count': len(taches_retard),
        'total_taches': Tache.objects.filter(ferme__in=fermes_qs, statut__in=['a_faire', 'en_cours']).count(),
    }
    
    return render(request, 'dashboard/bento_cards/_card_taches.html', context)


# =============================================================================
# CARTE BENTO: PRÉDICTIONS RÉCOLTE
# =============================================================================

@login_required
@require_GET
def bento_card_predictions(request: HttpRequest) -> HttpResponse:
    """
    Carte Bento: Prédictions de récolte (min/max) avec graphique sparkline.
    """
    from baay.models import PrevisionRecolte
    from django.db.models import Avg, Min, Max
    
    profile = request.user.profile
    projets_qs = projets_accessibles_qs(profile)
    
    previsions = PrevisionRecolte.objects.filter(
        projet__in=projets_qs,
    ).aggregate(
        avg_confiance=Avg('indice_confiance'),
        min_rendement=Min('rendement_estime_min'),
        max_rendement=Max('rendement_estime_max'),
        count=models.Count('id'),
    )
    
    # Récupérer les prévisions individuelles pour le graphique
    prev_list = PrevisionRecolte.objects.filter(
        projet__in=projets_qs,
    ).select_related('projet', 'projet_produit').order_by('-date_prediction')[:10]
    
    context = {
        'stats': previsions,
        'previsions': prev_list,
        'has_predictions': previsions['count'] > 0,
    }
    
    return render(request, 'dashboard/bento_cards/_card_predictions.html', context)


# =============================================================================
# API: CHATBOT AGRICOLE RAG
# =============================================================================

@login_required
@require_http_methods(['POST'])
def chatbot_agricole_query(request: HttpRequest) -> JsonResponse:
    """
    API endpoint pour le chatbot agricole (RAG).
    Accepte question JSON, retourne réponse avec sources.
    """
    import json
    
    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        
        if not question:
            return JsonResponse({'error': 'question_requise'}, status=400)
        
        # Limiter longueur
        if len(question) > 500:
            question = question[:500]
        
        # Requête RAG
        result = RAGService.repondre_question(question)
        
        return JsonResponse({
            'question': question,
            'reponse': result.reponse,
            'sources': result.sources,
            'confidence': round(result.confidence, 2),
            'query_time_ms': result.query_time_ms,
            'status': 'success',
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'json_invalide'}, status=400)
    except Exception as e:
        logger.exception("Erreur chatbot agricole")
        return JsonResponse({'error': 'erreur_serveur', 'detail': str(e)}, status=500)


# =============================================================================
# PARTIALS HTMX
# =============================================================================

@login_required
@require_GET
def partial_recommandation_detail(request: HttpRequest, recommandation_id: str) -> HttpResponse:
    """
    Partial HTMX: Détail d'une recommandation fertilisation.
    Pour affichage dans modal ou drawer.
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    
    reco = get_object_or_404(
        RecommandationFertilisation,
        pk=recommandation_id,
        historique_sol__ferme__in=fermes_qs,
    )
    
    return render(request, 'dashboard/partials/_recommandation_detail.html', {
        'recommandation': reco,
    })


@login_required
@require_GET
def partial_incident_detail(request: HttpRequest, incident_id: str) -> HttpResponse:
    """
    Partial HTMX: Détail d'un incident.
    """
    profile = request.user.profile
    fermes_qs = fermes_accessibles_qs(profile)
    
    incident = get_object_or_404(
        IncidentRapporte,
        pk=incident_id,
        ferme__in=fermes_qs,
    )
    
    return render(request, 'dashboard/partials/_incident_detail.html', {
        'incident': incident,
    })


# =============================================================================
# CARTES BENTO SIMPLE — Tâches & Messagerie (Baay Simple)
# =============================================================================

@login_required
@require_GET
def bento_card_taches_simple(request: HttpRequest) -> HttpResponse:
    """
    Carte Baay Simple : uniquement les tâches assignées à l'ouvrier connecté.
    Affichage visuel avec icônes agricoles et état couleur.
    """
    from baay.models import Tache
    from django.utils import timezone as tz

    profile = request.user.profile
    today = tz.localdate()

    taches = (
        Tache.objects.filter(
            assigne_a=profile,
            statut__in=['a_faire', 'en_cours'],
        )
        .select_related('ferme', 'projet')
        .order_by('date_echeance', '-date_creation')[:10]
    )

    # Enrichir avec état retard
    taches_data = []
    for t in taches:
        en_retard = t.date_echeance and t.date_echeance < today
        taches_data.append({'tache': t, 'en_retard': en_retard})

    return render(request, 'dashboard/bento_cards/_card_taches_simple.html', {
        'taches_data': taches_data,
        'total': len(taches_data),
    })


@login_required
@require_GET
def bento_card_messagerie_simple(request: HttpRequest) -> HttpResponse:
    """
    Carte Baay Simple : bouton micro géant + lien vers messagerie complète.
    Affiche les 3 derniers messages non lus de la ferme active.
    """
    from baay.models import Conversation, Message

    profile = request.user.profile

    # Dernières conversations de l'utilisateur
    last_msgs = (
        Message.objects.filter(conversation__participants=profile)
        .exclude(expediteur=profile)
        .exclude(lu_par=profile)
        .select_related('expediteur__user', 'conversation')
        .order_by('-date_envoi')[:3]
    )

    return render(request, 'dashboard/bento_cards/_card_messagerie_simple.html', {
        'messages_recents': last_msgs,
        'unread_count': last_msgs.count(),
    })
