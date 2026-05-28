from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from baay.models import InvitationFerme, Ferme, Profile, MembreFerme

# Mapping from invitation role values (English) to MembreFerme role values (French)
ROLE_INVITE_TO_MEMBRE = {
    'technician': 'technicien',
    'worker': 'ouvrier',
}


@login_required
@require_http_methods(["POST"])
def creer_invitation(request, ferme_id):
    """Le propriétaire crée un lien d'invitation pour sa ferme."""
    ferme = get_object_or_404(Ferme, pk=ferme_id, proprietaire=request.user.profile)
    role_invite = request.POST.get('role_invite', 'technician')
    if role_invite not in ('technician', 'worker'):
        role_invite = 'technician'
    invitation = InvitationFerme.objects.create(
        ferme=ferme,
        cree_par=request.user.profile,
        role_invite=role_invite,
    )
    lien = request.build_absolute_uri(f'/rejoindre/{invitation.token}/')
    return render(request, 'invitations/_lien.html', {
        'lien': lien,
        'ferme': ferme,
        'invitation': invitation,
    })


@require_http_methods(["GET", "POST"])
def rejoindre_ferme(request, token):
    """Technicien ou ouvrier rejoint une ferme via un lien d'invitation."""
    invitation = get_object_or_404(InvitationFerme, token=token)

    if not invitation.is_valid:
        raison = 'expiree' if invitation.utilisee else 'delai'
        return render(request, 'invitations/invalide.html', {'raison': raison})

    if request.method == "GET":
        if request.user.is_authenticated:
            return render(request, 'invitations/confirmer.html', {'invitation': invitation})
        return render(request, 'invitations/inscription.html', {
            'invitation': invitation,
            'token': token,
        })

    # POST
    action = request.POST.get('action', 'inscription')

    if action == 'confirmer' and request.user.is_authenticated:
        _rattacher_membre(request.user.profile, invitation)
        messages.success(request, f"Vous avez rejoint la ferme {invitation.ferme.nom}.")
        return redirect('dashboard')

    # Inscription nouvelle
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    prenom = request.POST.get('prenom', '').strip()
    nom = request.POST.get('nom', '').strip()

    if not email or not password or len(password) < 8:
        return render(request, 'invitations/inscription.html', {
            'invitation': invitation,
            'token': token,
            'error': 'Email et mot de passe (8 caractères min) requis.',
        })

    if User.objects.filter(email=email).exists():
        return render(request, 'invitations/inscription.html', {
            'invitation': invitation,
            'token': token,
            'error': "Un compte avec cet email existe déjà. Connectez-vous d'abord.",
        })

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=prenom,
        last_name=nom,
    )
    # Profile créé via signal (post_save) ou manuellement si absent
    profile = getattr(user, 'profile', None)
    if not profile:
        profile = Profile.objects.create(user=user)
    profile.onboarding_completed = True  # skip l'onboarding wizard standard
    profile.save()

    _rattacher_membre(profile, invitation)

    from django.contrib.auth import authenticate, login
    authenticated_user = authenticate(username=email, password=password)
    if authenticated_user:
        login(request, authenticated_user)

    messages.success(request, f"Bienvenue ! Vous avez rejoint la ferme {invitation.ferme.nom}.")
    return redirect('detail_ferme', ferme_id=invitation.ferme.pk)


def _rattacher_membre(profile, invitation):
    """Rattache le profil à la ferme via MembreFerme et invalide l'invitation."""
    ferme = invitation.ferme
    role_membre = ROLE_INVITE_TO_MEMBRE.get(invitation.role_invite, 'ouvrier')
    MembreFerme.objects.get_or_create(
        ferme=ferme,
        utilisateur=profile,
        defaults={'role': role_membre},
    )
    invitation.utilisee = True
    invitation.save(update_fields=['utilisee'])
