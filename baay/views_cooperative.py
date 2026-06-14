"""Gestion des coopératives (Phase 3) : détail, adhésion, rattachement de
ferme et gestion des membres/rôles."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Cooperative, Ferme, MembreCooperative
from .permissions import (
    cooperatives_accessibles_qs,
    peut_gerer_cooperative,
    role_dans_cooperative,
    roles_coop_assignables_par,
)


@login_required
def cooperative_detail(request, coop_id):
    profile = request.user.profile
    coop = get_object_or_404(Cooperative, id=coop_id)
    role = role_dans_cooperative(profile, coop)
    if role is None:
        messages.error(request, "Vous n'êtes pas membre de cette coopérative.")
        return redirect('dashboard')

    is_admin = peut_gerer_cooperative(profile, coop)
    membres = coop.membres.select_related('utilisateur__user').order_by('role', 'date_adhesion')
    fermes = coop.fermes.select_related('proprietaire__user').order_by('nom')
    mes_fermes_rattachables = Ferme.objects.filter(
        proprietaire=profile, cooperative__isnull=True,
    ).order_by('nom')

    return render(request, 'cooperatives/detail.html', {
        'cooperative': coop,
        'role': role,
        'is_admin': is_admin,
        'membres': membres,
        'fermes': fermes,
        'roles_assignables': roles_coop_assignables_par(role),
        'mes_fermes_rattachables': mes_fermes_rattachables,
        'role_choices': MembreCooperative.ROLE_CHOICES,
        'mon_id': profile.id,
    })


@login_required
def rejoindre_cooperative(request):
    """Rejoindre une coopérative via son code (devient fermier affilié)."""
    profile = request.user.profile
    if request.method == 'POST':
        code = (request.POST.get('code') or '').strip().upper()
        coop = Cooperative.objects.filter(code_acces=code).first()
        if not coop:
            messages.error(request, "Code de coopérative invalide.")
        else:
            membre, created = MembreCooperative.objects.get_or_create(
                cooperative=coop, utilisateur=profile,
                defaults={'role': MembreCooperative.ROLE_FERMIER_AFFILIE},
            )
            if created:
                messages.success(request, f"Vous avez rejoint « {coop.nom} ».")
            else:
                messages.info(request, f"Vous êtes déjà membre de « {coop.nom} ».")
            return redirect('cooperative_detail', coop_id=coop.id)
    return render(request, 'cooperatives/rejoindre.html')


@login_required
@require_POST
def rattacher_ferme_cooperative(request, coop_id):
    """Le propriétaire rattache l'une de ses fermes à la coopérative."""
    profile = request.user.profile
    coop = get_object_or_404(Cooperative, id=coop_id)
    if role_dans_cooperative(profile, coop) is None:
        messages.error(request, "Vous n'êtes pas membre de cette coopérative.")
        return redirect('dashboard')
    ferme = get_object_or_404(Ferme, id=request.POST.get('ferme'), proprietaire=profile)
    ferme.cooperative = coop
    ferme.save()
    messages.success(request, f"« {ferme.nom} » est désormais affiliée à la coopérative.")
    return redirect('cooperative_detail', coop_id=coop.id)


@login_required
@require_POST
def detacher_ferme_cooperative(request, coop_id):
    """Le propriétaire retire sa ferme de la coopérative."""
    profile = request.user.profile
    coop = get_object_or_404(Cooperative, id=coop_id)
    ferme = get_object_or_404(Ferme, id=request.POST.get('ferme'), proprietaire=profile, cooperative=coop)
    ferme.cooperative = None
    ferme.save()
    messages.success(request, f"« {ferme.nom} » a été retirée de la coopérative.")
    return redirect('cooperative_detail', coop_id=coop.id)


@login_required
@require_POST
def cooperative_changer_role(request, coop_id, membre_id):
    """Un admin modifie le rôle d'un membre (selon ce qu'il peut assigner)."""
    profile = request.user.profile
    coop = get_object_or_404(Cooperative, id=coop_id)
    if not peut_gerer_cooperative(profile, coop):
        messages.error(request, "Seul un administrateur peut gérer les membres.")
        return redirect('cooperative_detail', coop_id=coop.id)

    membre = get_object_or_404(MembreCooperative, id=membre_id, cooperative=coop)
    if membre.utilisateur_id == profile.id:
        messages.error(request, "Vous ne pouvez pas modifier votre propre rôle.")
        return redirect('cooperative_detail', coop_id=coop.id)

    nouveau = request.POST.get('role')
    assignables = roles_coop_assignables_par(role_dans_cooperative(profile, coop))
    if nouveau in assignables:
        membre.role = nouveau
        membre.save(update_fields=['role'])
        messages.success(request, "Rôle mis à jour.")
    else:
        messages.error(request, "Ce rôle ne peut pas être assigné.")
    return redirect('cooperative_detail', coop_id=coop.id)


@login_required
@require_POST
def cooperative_retirer_membre(request, coop_id, membre_id):
    """Un admin retire un membre. On garde toujours au moins un admin."""
    profile = request.user.profile
    coop = get_object_or_404(Cooperative, id=coop_id)
    if not peut_gerer_cooperative(profile, coop):
        messages.error(request, "Seul un administrateur peut gérer les membres.")
        return redirect('cooperative_detail', coop_id=coop.id)

    membre = get_object_or_404(MembreCooperative, id=membre_id, cooperative=coop)
    if membre.role == MembreCooperative.ROLE_ADMIN:
        nb_admins = coop.membres.filter(role=MembreCooperative.ROLE_ADMIN).count()
        if nb_admins <= 1:
            messages.error(request, "Impossible de retirer le dernier administrateur.")
            return redirect('cooperative_detail', coop_id=coop.id)

    membre.delete()
    messages.success(request, "Membre retiré de la coopérative.")
    return redirect('cooperative_detail', coop_id=coop.id)
