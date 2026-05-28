from django.db.models import Sum, Count, Q, F, Avg, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache

from baay.models import (
    Projet, Ferme, MembreFerme, Tache, ProduitAgricole,
    Investissement, Message, ParticipationConversation, ProjetProduit
)
from baay.permissions import (
    projets_accessibles_qs, projets_accessibles_kpi_roi_qs,
    peut_voir_investissements_any, fermes_accessibles_qs
)
from baay import dashboard_services
from baay.core_services import investissement_montant_expr, calculer_kpis_financiers_par_projet


def get_unified_dashboard_context(request, utilisateur, selected_ferme=None, farms_qs=None):
    today = timezone.now().date()

    # ── 1. Base Querysets ────────────────────────────────────────────────────
    if farms_qs is None:
        user_fermes = fermes_accessibles_qs(utilisateur).distinct().order_by('nom')
    else:
        user_fermes = farms_qs

    projets_qs = projets_accessibles_qs(utilisateur).select_related(
        'culture', 'localite', 'ferme'
    ).prefetch_related('projet_produits__produit', 'taches')

    if selected_ferme:
        projets_qs = projets_qs.filter(ferme=selected_ferme)

    # ── 2. Strategic Aggregates — une seule requête DB ───────────────────────
    agg = projets_qs.aggregate(
        superficie_sum=Coalesce(Sum('superficie'), Value(Decimal('0'))),
        rendement_sum=Coalesce(Sum('rendement_estime'), Value(Decimal('0'))),
        total=Count('id'),
        en_cours=Count('id', filter=Q(statut='en_cours')),
        en_pause=Count('id', filter=Q(statut='en_pause')),
        finis=Count('id', filter=Q(statut__in=('fini', Projet.STATUT_CLOTURE))),
    )
    superficie_totale = float(agg['superficie_sum'])
    rendement_total = float(agg['rendement_sum'])
    rendement_moyen_global = rendement_total / superficie_totale if superficie_totale > 0 else 0
    projets_en_cours = agg['en_cours']
    projets_en_pause = agg['en_pause']
    projets_finis = agg['finis']
    total_count = agg['total']
    completion_rate = round((projets_finis / total_count) * 100) if total_count else 0

    roi_scope_projets = projets_accessibles_kpi_roi_qs(utilisateur, projets_qs)
    cockpit_payload = dashboard_services.cockpit_payload(projets_qs, roi_scope_projets)

    # ── 3a. Cultures data — 1 requête agrégée au lieu de N×3 ────────────────
    culture_agg_rows = (
        projets_qs
        .filter(culture__isnull=False)
        .values('culture__id', 'culture__nom', 'culture__rendement_moyen')
        .annotate(
            superficie=Coalesce(Sum('superficie'), Value(Decimal('0'))),
            rendement_total=Coalesce(Sum('rendement_estime'), Value(Decimal('0'))),
            projets_count=Count('id'),
        )
        .order_by('-superficie')
    )
    cultures_data = []
    for row in culture_agg_rows:
        sup = float(row['superficie'])
        rend = float(row['rendement_total'])
        rend_ha = round(rend / sup, 1) if sup > 0 else 0
        rend_moyen = float(row['culture__rendement_moyen'] or 0)
        efficiency = round((rend_ha / rend_moyen) * 100) if rend_moyen and rend_ha > 0 else 100
        cultures_data.append({
            'culture': {'nom': row['culture__nom'], 'id': row['culture__id']},
            'superficie': sup,
            'rendement_total': rend,
            'rendement_par_ha': rend_ha,
            'efficiency_score': efficiency,
            'projets_count': row['projets_count'],
        })

    # ── 3b. Fermes performance — 1 requête agrégée au lieu de N×3 ───────────
    ferme_agg_rows = (
        projets_qs
        .values('ferme__id', 'ferme__nom', 'ferme__superficie_totale',
                'ferme__latitude', 'ferme__longitude')
        .annotate(
            superficie_utilisee=Coalesce(Sum('superficie'), Value(Decimal('0'))),
            rendement_total=Coalesce(Sum('rendement_estime'), Value(Decimal('0'))),
            projets_actifs=Count('id', filter=Q(statut='en_cours')),
        )
        .order_by('ferme__nom')
    )
    ferme_agg_map = {
        row['ferme__id']: row for row in ferme_agg_rows
    }

    fermes_performance = []
    map_markers = []
    weather_ferme_id = None
    for f in user_fermes:
        row = ferme_agg_map.get(f.id, {})
        f_sup = float(row.get('superficie_utilisee') or 0)
        f_rend = float(row.get('rendement_total') or 0)
        f_total_sup = float(f.superficie_totale) if f.superficie_totale else 1.0
        f_util = round((f_sup / f_total_sup) * 100, 1)
        fermes_performance.append({
            'ferme': f,
            'superficie_utilisee': f_sup,
            'rendement_total': f_rend,
            'taux_utilisation': f_util,
            'projets_actifs': row.get('projets_actifs') or 0,
        })
        if f.latitude and f.longitude:
            map_markers.append({
                'lat': float(f.latitude),
                'lng': float(f.longitude),
                'title': f.nom,
            })
            if weather_ferme_id is None:
                weather_ferme_id = str(f.id)

    # Ferme sélectionnée : override map_markers et weather
    if selected_ferme and selected_ferme.latitude and selected_ferme.longitude:
        map_markers = [{
            'lat': float(selected_ferme.latitude),
            'lng': float(selected_ferme.longitude),
            'title': selected_ferme.nom,
        }]
        weather_ferme_id = str(selected_ferme.id)

    # ── 4. Agent Productivity — 1 requête agrégée ───────────────────────────
    taches_global_qs = Tache.objects.filter(ferme__in=user_fermes)
    if selected_ferme:
        taches_global_qs = taches_global_qs.filter(ferme=selected_ferme)

    agents_stats = list(taches_global_qs.values(
        'assigne_a__id', 'assigne_a__user__username',
        'assigne_a__user__first_name', 'assigne_a__user__last_name'
    ).annotate(
        total_taches=Count('id'),
        terminees=Count('id', filter=Q(statut='terminee')),
        a_temps=Count('id', filter=Q(statut='terminee', date_terminee__lte=F('date_echeance'))),
        en_retard=Count('id', filter=Q(date_echeance__lt=today, statut__in=['a_faire', 'en_cours'])),
    ).order_by('-terminees'))

    agents_performance = []
    max_terminees = max((a['terminees'] for a in agents_stats), default=0)
    for a in agents_stats:
        nom = (
            f"{a['assigne_a__user__first_name'] or ''} {a['assigne_a__user__last_name'] or ''}".strip()
            or a['assigne_a__user__username']
        )
        taux = round(a['terminees'] / a['total_taches'] * 100, 1) if a['total_taches'] > 0 else 0
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
            'score_global': score,
        })

    # ── 5. Activities & Tasks — agrégation unique ────────────────────────────
    taches_activite_qs = (
        Tache.objects.filter(projet__in=projets_qs)
        .exclude(statut__in=['terminee', 'annulee'])
        .select_related('projet', 'assigne_a__user')
    )
    taches_retard = list(taches_activite_qs.filter(date_echeance__lt=today).order_by('date_echeance')[:10])
    taches_urgentes = list(taches_activite_qs.filter(
        date_echeance__gte=today,
        date_echeance__lte=today + timedelta(days=7)
    ).order_by('date_echeance')[:10])

    stats_taches_agg = taches_activite_qs.aggregate(
        total=Count('id'),
        en_retard=Count('id', filter=Q(date_echeance__lt=today)),
        a_venir=Count('id', filter=Q(date_echeance__gte=today, date_echeance__lte=today + timedelta(days=7))),
        en_cours=Count('id', filter=Q(statut='en_cours')),
    )
    stats_taches = {
        'total': stats_taches_agg['total'],
        'en_retard': stats_taches_agg['en_retard'],
        'a_venir': stats_taches_agg['a_venir'],
        'en_cours': stats_taches_agg['en_cours'],
    }

    last_week = timezone.now() - timedelta(days=7)
    tasks_done_last_week = Tache.objects.filter(
        ferme__in=user_fermes,
        statut='terminee',
        date_terminee__gte=last_week,
    ).count()

    # ── 6. Alertes projets ───────────────────────────────────────────────────
    alertes_projets = [
        {'type': 'pause', 'projet': p, 'message': f"Projet en pause : {p.nom}"}
        for p in Projet.objects.filter(
            id__in=projets_qs.filter(statut='en_pause').values('id')[:5]
        ).only('id', 'nom')
    ]

    # ── 7. Burn rates — 1 requête agrégée au lieu de N×1 ────────────────────
    burn_rates = []
    if roi_scope_projets.exists():
        inv_expr = investissement_montant_expr()
        inv_by_projet = dict(
            Investissement.objects.filter(projet__in=roi_scope_projets)
            .values('projet_id')
            .annotate(s=Coalesce(Sum(inv_expr), Value(Decimal('0'))))
            .values_list('projet_id', 's')
        )
        for p in Projet.objects.filter(
            id__in=roi_scope_projets.values('id')
        ).only('id', 'nom', 'date_lancement'):
            if not p.date_lancement:
                continue
            days_elapsed = max((today - p.date_lancement).days, 1)
            total_spent = float(inv_by_projet.get(p.id, 0))
            burn_rates.append({'projet': p, 'burn_rate': round(total_spent / days_elapsed, 0)})

    # ── 8. Messaging feed ───────────────────────────────────────────────────
    messages_recents = (
        Message.objects.filter(conversation__participants=utilisateur)
        .exclude(expediteur=utilisateur)
        .select_related('expediteur__user', 'conversation')
        .order_by('-date_envoi')[:5]
    )

    # ── 9. Next Harvest ──────────────────────────────────────────────────────
    prochaine_recolte = (
        ProjetProduit.objects.filter(
            projet__in=projets_qs,
            date_recolte_prevue__gte=today,
        )
        .select_related('produit')
        .order_by('date_recolte_prevue')
        .first()
    )

    # ── 10. Dashboard stats JSON for immediate chart rendering ────────────────
    # Évite l'appel API /api/dashboard/stats/ asynchrone qui ralentit le chargement
    import json
    from django.utils.html import mark_safe

    # Format projets pour le JS (similaire à dashboard_stats_api)
    projets_list = []
    for p in projets_qs[:100]:  # Limiter à 100 projets pour la taille du JSON
        projets_list.append({
            'id': str(p.id),
            'nom': p.nom,
            'statut': p.statut,
            'culture_id': str(p.culture.id) if p.culture else '',
            'culture_nom': p.culture.nom if p.culture else 'N/A',
            'superficie': float(p.superficie) if p.superficie else 0,
            'rendement_estime': float(p.rendement_estime) if p.rendement_estime else 0,
            'date_lancement': p.date_lancement.strftime('%Y-%m-%d') if p.date_lancement else '',
            'ferme_nom': p.ferme.nom if p.ferme else '',
        })

    # Format cultures pour les graphiques
    projets_par_culture = [
        {
            'culture': c['culture']['nom'],
            'count': c['projets_count'],
            'superficie': c['superficie'],
            'rendement': c['rendement_total']
        }
        for c in cultures_data
    ]

    # Stats par statut
    projets_par_statut = []
    for statut, label in [('en_cours', 'En cours'), ('en_pause', 'En pause'), ('fini', 'Terminé')]:
        count = projets_qs.filter(statut=statut).count()
        if count > 0:
            projets_par_statut.append({'statut': statut, 'count': count})

    dashboard_stats_data = {
        'superficie_totale': superficie_totale,
        'rendement_total': rendement_total,
        'investissement_total': float(cockpit_payload.get('investissement_total', 0)),
        'nb_projets': total_count,
        'projets_en_cours': projets_en_cours,
        'projets_en_pause': projets_en_pause,
        'projets_finis': projets_finis,
        'completion_rate': completion_rate,
        'projets_par_statut': projets_par_statut,
        'projets_par_culture': projets_par_culture,
        'nombre_fermes': len(user_fermes),
        'fermes_data': [
            {
                'id': str(f['ferme'].id),
                'nom': f['ferme'].nom,
                'projets_count': f['ferme'].projets_count_ann or 0,
                'projets_actifs': f['ferme'].projets_actifs_ann or 0,
                'superficie_ferme': float(f['ferme'].superficie_totale or 0),
                'superficie_utilisee': f['superficie_utilisee'],
                'membres_count': (f['ferme'].membres_count_ann or 0) + 1,
                'utilisation_pct': f['taux_utilisation'],
            }
            for f in fermes_performance
        ],
        'selected_ferme': {
            'id': str(selected_ferme.id),
            'nom': selected_ferme.nom,
            'utilisation': round(
                sum(p.superficie or 0 for p in projets_qs.filter(ferme=selected_ferme, statut='en_cours')) /
                float(selected_ferme.superficie_totale or 1) * 100, 1
            ) if selected_ferme else 0,
            'membres': (selected_ferme.membres_count_ann or 0) + 1,
        } if selected_ferme else None,
        'projets_list': projets_list,
        'quick_stats': cockpit_payload.get('quick_stats', {}),
        'finance_monthly': cockpit_payload.get('finance_monthly', {'mois': [], 'recettes': [], 'depenses': []}),
        'invest_by_category': cockpit_payload.get('invest_by_category', {'labels': [], 'values': []}),
    }

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
        'nombre_fermes': len(user_fermes),
        'messages_recents': messages_recents,
        'ferme_utilisation': (
            round(sum(f['taux_utilisation'] for f in fermes_performance) / len(fermes_performance), 1)
            if fermes_performance else 0
        ),
        'taches_retard': taches_retard,
        'taches_urgentes': taches_urgentes,
        'stats_taches': stats_taches,
        'tasks_velocity': tasks_done_last_week,
        'alertes_projets': alertes_projets,
        'burn_rates': burn_rates[:5],
        'prochaine_recolte': prochaine_recolte,
        'map_markers': map_markers,
        'dashboard_stats_json': mark_safe(json.dumps(dashboard_stats_data, default=str)),
    }
