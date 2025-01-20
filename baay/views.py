from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages

from baay.forms import CustomUserCreationForm, ProjetForm, InvestissementForm
from baay.models import Profile, Projet, Investissement


# Vue pour la page d'accueil
def home_view(request):
    return render(request, 'home.html')

# Vue pour l'inscription
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # Enregistre l'utilisateur
            # Créez un profil utilisateur avec le numéro de téléphone
            Profile.objects.create(
                user=user,
                phone_number=form.cleaned_data['phone_number']
            )
            login(request, user)
            messages.success(request, "Inscription réussie ! Vous êtes maintenant connecté.")
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'auth/register.html', {'form': form})

# Vue pour la connexion
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Bienvenue, {username} !")
                return redirect('home')
            else:
                messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    else:
        form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})

# Vue pour la déconnexion
def logout_view(request):
    logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect('home')


@login_required
def creer_projet(request):
    if request.method == 'POST':
        projet_form = ProjetForm(request.POST)
        if projet_form.is_valid():
            # Sauvegarder le projet en associant l'utilisateur connecté
            projet = projet_form.save(commit=False)
            projet.utilisateur = request.user.profile  # Associer le profil de l'utilisateur connecté
            projet.save()
            messages.success(request, "Le projet a été créé avec succès.")
            return redirect('liste_projets')
    else:
        projet_form = ProjetForm()

    return render(request, 'projets/creer_projet.html', {
        'projet_form': projet_form,
    })

@login_required
def modifier_projet(request, projet_id):
    projet = get_object_or_404(Projet, id=projet_id, utilisateur=request.user.profile)

    if request.method == 'POST':
        projet_form = ProjetForm(request.POST, instance=projet)
        if projet_form.is_valid():
            projet_form.save()
            messages.success(request, "Le projet a été modifié avec succès.")
            return redirect('detail_projet', projet_id=projet.id)
    else:
        projet_form = ProjetForm(instance=projet)

    return render(request, 'projets/modifier_projet.html', {
        'projet_form': projet_form,
        'projet': projet,
    })

@login_required
def supprimer_projet(request, projet_id):
    projet = get_object_or_404(Projet, id=projet_id, utilisateur=request.user.profile)

    if request.method == 'POST':
        projet.delete()
        messages.success(request, "Le projet a été supprimé avec succès.")
        return redirect('liste_projets')

    return render(request, 'projets/confirmer_suppression.html', {
        'projet': projet,
    })

@login_required
def ajouter_investissement(request, projet_id):
    projet = get_object_or_404(Projet, id=projet_id, utilisateur=request.user.profile)

    if request.method == 'POST':
        investissement_form = InvestissementForm(request.POST)
        if investissement_form.is_valid():
            investissement = investissement_form.save(commit=False)
            investissement.projet = projet  # Associer l'investissement au projet
            investissement.save()
            messages.success(request, "L'investissement a été ajouté avec succès.")
            return redirect('detail_projet', projet_id=projet.id)
    else:
        investissement_form = InvestissementForm()

    return render(request, 'projets/ajouter_investissement.html', {
        'investissement_form': investissement_form,
        'projet': projet,
    })

@login_required
def detail_projet(request, projet_id):
    projet = get_object_or_404(Projet, id=projet_id, utilisateur=request.user.profile)
    investissements = projet.investissement_set.all()  # Récupérer tous les investissements du projet
    return render(request, 'projets/detail_projet.html', {
        'projet': projet,
        'investissements': investissements,
    })

@login_required
def liste_projets(request):
    projets_list = Projet.objects.filter(utilisateur=request.user.profile).order_by('-date_lancement')  # Ordonner par date de lancement
    paginator = Paginator(projets_list, 10)  # Affichez 10 projets par page
    page_number = request.GET.get('page')
    projets = paginator.get_page(page_number)
    return render(request, 'projets/liste_projets.html', {'projets': projets})
