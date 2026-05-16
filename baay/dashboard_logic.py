from django.db.models import Sum, Count, Q, F, Avg
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from baay.models import Projet, Ferme, MembreFerme, Tache, ProduitAgricole, Investissement, Message, ParticipationConversation, ProjetProduit
from baay.permissions import projets_accessibles_qs, projets_accessibles_kpi_roi_qs, peut_voir_investissements_any, fermes_accessibles_qs
from baay import dashboard_services
from baay.core_services import investissement_montant_expr, calculer_kpis_financiers_par_projet
from django.db.models.functions import Coalesce

def get_unified_dashboard_context(request, utilisateur, selected_ferme=None, farms_qs=None):
    today = timezone.now().date()

    # 1. Base Querysets
    if farms_qs is None:
        user_fermes = fermes_accessibles_qs(utilisateur).distinct().order_by('nom')
    else:
        user_fermes = farms_qs

    projets_qs = projets_accessibles_qs(utilisateur).select_related(
        'culture', 'localite', 'ferme'
    ).prefetch_related('projet_produits__produit', 'taches')

    if selected_ferme:
        projets_qs = projets_qs.filter(ferme=selected_ferme)

    # 2. Strategic Aggregates (Cockpit)
    superficie_totale = projets_qs.aggregate(Sum('superficie'))['superficie__sum'] or 0
    rendement_total = projets_qs.aggregate(Sum('rendement_estime'))['rendement_estime__sum'] or 0
    rendement_moyen_global = float(rendement_total) / float(superficie_totale) if superficie_totale > 0 else 0

    projets_en_cours = projets_qs.filter(statut='en_cours').count()
    projets_en_pause = projets_qs.filter(statut='en_pause').count()
    projets_finis = projets_qs.filter(statut__in=('fini', Projet.STATUT_CLOTURE)).count()
    total_count = projets_qs.count()
    completion_rate = round((projets_finis / total_count) * 100) if total_count else 0

    roi_scope_projets = projets_accessibles_kpi_roi_qs(utilisateur, projets_qs)
    cockpit_payload = dashboard_services.cockpit_payload(projets_qs, roi_scope_projets)

    # 3. Performance Data (Analytics)
    cultures_data = []
    cultures = ProduitAgricole.objects.filter(projet__in=projets_qs).distinct()
    for culture in cultures:
        p_culture = projets_qs.filter(culture=culture)
        sup = p_culture.aggregate(Sum('superficie'))['superficie__sum'] or 0
        rend = p_culture.aggregate(Sum('rendement_estime'))['rendement_estime__sum'] or 0
        rend_ha = round(float(rend) / float(sup), 1) if sup > 0 else 0

        # New KPI: Surface Efficiency (Performance relative to culture average)
        efficiency = 100
        if culture.rendement_moyen and rend_ha > 0:
            efficiency = round((rend_ha / float(culture.rendement_moyen)) * 100)

        cultures_data.append({
            'culture': culture,
            'superficie': sup,
            'rendement_total': rend,
            'rendement_par_ha': rend_ha,
            'efficiency_score': efficiency,
            'projets_count': p_culture.count(),
        })

    fermes_performance = []
    for f in user_fermes:
        f_proj = projets_qs.filter(ferme=f)
        f_sup = f_proj.aggregate(Sum('superficie'))['superficie__sum'] or 0
        f_rend = f_proj.aggregate(Sum('rendement_estime'))['rendement_estime__sum'] or 0
        f_total_sup = float(f.superficie_totale) if f.superficie_totale else 1.0
        f_util = round((float(f_sup) / f_total_sup) * 100, 1)

        fermes_performance.append({
            'ferme': f,
            'superficie_utilisee': f_sup,
            'rendement_total': f_rend,
            'taux_utilisation': f_util,
            'projets_actifs': f_proj.filter(statut='en_cours').count(),
        })

    # Agent Productivity
    taches_global_qs = Tache.objects.filter(ferme__in=user_fermes)
    if selected_ferme:
        taches_global_qs = taches_global_qs.filter(ferme=selected_ferme)

    agents_stats = taches_global_qs.values(
        'assigne_a__id', 'assigne_a__user__username', 'assigne_a__user__first_name', 'assigne_a__user__last_name'
    ).annotate(
        total_taches=Count('id'),
        terminees=Count('id', filter=Q(statut='terminee')),
        a_temps=Count('id', filter=Q(statut='terminee', date_terminee__lte=F('date_echeance'))),
        en_retard=Count('id', filter=Q(date_echeance__lt=today, statut__in=['a_faire', 'en_cours'])),
    ).order_by('-terminees')

    agents_performance = []
    max_terminees = max((a['terminees'] for a in agents_stats), default=0)
    for a in agents_stats:
        nom = f"{a['assigne_a__user__first_name'] or ''} {a['assigne_a__user__last_name'] or ''}".strip() or a['assigne_a__user__username']
        taux = round((a['terminees'] / a['total_taches'] * 100), 1) if a['total_taches'] > 0 else 0
        taux_temps = (a['a_temps'] / a['terminees'] * 100) if a['terminees'] > 0 else 0
        vol_score = (a['terminees'] / max_terminees * 100) if max_terminees > 0 else 0
        score = round((taux_temps * 0.6) + (vol_score * 0.4), 1)

        agents_performance.append({
            'nom': nom,
            'username': a['assigne_a__user__username'],
            'total_taches': a['total_taches'],
            'terminees': a['terminees'],
            'a_temps': a['a_temps'],
            'en_retard': a['en_retard'],
            'taux_completion': taux,
            'score_global': score
        })

    # 4. Activities & Tasks
    taches_activite_qs = Tache.objects.filter(
        projet__in=projets_qs
    ).exclude(statut__in=['terminee', 'annulee']).select_related('projet', 'assigne_a__user')

    taches_retard = taches_activite_qs.filter(date_echeance__lt=today).order_by('date_echeance')[:10]
    taches_urgentes = taches_activite_qs.filter(
        date_echeance__gte=today,
        date_echeance__lte=today + timedelta(days=7)
    ).order_by('date_echeance')[:10]

    stats_taches = {
        'total': taches_activite_qs.count(),
        'en_retard': taches_activite_qs.filter(date_echeance__lt=today).count(),
        'a_venir': taches_activite_qs.filter(date_echeance__gte=today, date_echeance__lte=today + timedelta(days=7)).count(),
        'en_cours': taches_activite_qs.filter(statut='en_cours').count(),
    }

    # New KPI: Task Velocity (completed last 7 days)
    last_week = timezone.now() - timedelta(days=7)
    tasks_done_last_week = Tache.objects.filter(
        ferme__in=user_fermes,
        statut='terminee',
        date_terminee__gte=last_week
    ).count()

    # Alerts
    alertes_projets = []
    for p in projets_qs.filter(statut='en_pause')[:5]:
        alertes_projets.append({'type': 'pause', 'projet': p, 'message': f"Projet en pause : {p.nom}"})

    # 5. New KPI: Budget Burn Rate
    # (Simplified: sum of all investments vs time elapsed)
    burn_rates = []
    if roi_scope_projets.exists():
        for p in roi_scope_projets:
            days_elapsed = (today - p.date_lancement).days
            if days_elapsed <= 0: days_elapsed = 1
            total_spent = Investissement.objects.filter(projet=p).aggregate(s=Sum(investissement_montant_expr()))['s'] or 0
            burn_rate = float(total_spent) / days_elapsed
            burn_rates.append({'projet': p, 'burn_rate': round(burn_rate, 0)})

    # 6. Messaging feed
    messages_recents = Message.objects.filter(
        conversation__participants=utilisateur
    ).exclude(expediteur=utilisateur).select_related('expediteur__user', 'conversation').order_by('-date_envoi')[:5]

    # 7. Next Harvest
    prochaine_recolte = ProjetProduit.objects.filter(
        projet__in=projets_qs,
        date_recolte_prevue__gte=today
    ).order_by('date_recolte_prevue').first()

    # 8. Map Data
    map_markers = []
    if selected_ferme and selected_ferme.latitude and selected_ferme.longitude:
        map_markers.append({
            'lat': float(selected_ferme.latitude),
            'lng': float(selected_ferme.longitude),
            'title': selected_ferme.nom
        })
    else:
        for f in user_fermes:
            if f.latitude and f.longitude:
                map_markers.append({
                    'lat': float(f.latitude),
                    'lng': float(f.longitude),
                    'title': f.nom
                })

    # 9. Weather Logic
    weather_ferme_id = None
    if selected_ferme and selected_ferme.latitude:
        weather_ferme_id = str(selected_ferme.id)
    else:
        for wf in user_fermes:
            if wf.latitude:
                weather_ferme_id = str(wf.id)
                break

    return {
        'projets': projets_qs.order_by('-date_lancement'),
        'projets_en_cours': projets_en_cours,
        'projets_en_pause': projets_en_pause,
        'projets_finis': projets_finis,
        'superficie_totale': superficie_totale,
        'rendement_total': rendement_total,
        'rendement_moyen_global': round(rendement_moyen_global, 1),
        'completion_rate': completion_rate,
        'cockpit': cockpit_payload,
        'can_view_investissements': peut_voir_investissements_any(utilisateur),
        'cultures_data': cultures_data,
        'fermes_performance': fermes_performance,
        'agents_performance': agents_performance,
        'fermes': user_fermes,
        'selected_ferme': selected_ferme,
        'dashboard_weather_ferme_id': weather_ferme_id,
        'nombre_fermes': user_fermes.count() if hasattr(user_fermes, 'count') else len(user_fermes),
        'messages_recents': messages_recents,
        'ferme_utilisation': round(sum(f['taux_utilisation'] for f in fermes_performance)/len(fermes_performance), 1) if fermes_performance else 0,

        # Activities components
        'taches_retard': taches_retard,
        'taches_urgentes': taches_urgentes,
        'stats_taches': stats_taches,
        'tasks_velocity': tasks_done_last_week,
        'alertes_projets': alertes_projets,
        'burn_rates': burn_rates[:5],
        'prochaine_recolte': prochaine_recolte,
        'map_markers': map_markers,
    }
