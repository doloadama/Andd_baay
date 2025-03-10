import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Sum
from django.db.models import Sum

from baay import models
from baay.forms import CustomUserCreationForm, ProjetForm, InvestissementForm
from baay.models import Profile, Projet, Investissement, ProduitAgricole, PredictionRendement, Localite
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error


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

class CustomPasswordResetView(PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')


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

logger = logging.getLogger(__name__)

@login_required
def modifier_projet(request, projet_id):
    projet = get_object_or_404(Projet, id=projet_id, utilisateur=request.user.profile)

    if request.method == 'POST':
        projet_form = ProjetForm(request.POST, instance=projet)
        if projet_form.is_valid():
            projet_form.save()
            messages.success(request, "Le projet a été modifié avec succès.")
            logger.debug(f"Projet {projet.id} modifié avec succès.")
            return redirect('detail_projet', projet_id=projet.id)
        else:
            logger.error(f"Erreurs dans le formulaire : {projet_form.errors}")
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
    projet = get_object_or_404(Projet, id=projet_id)

    if request.method == 'POST':
        investissement_form = InvestissementForm(request.POST)
        if investissement_form.is_valid():
            investissement = investissement_form.save(commit=False)
            investissement.projet = projet  # Associer l'investissement au projet
            investissement.save()
            return redirect('detail_projet', projet_id=projet.id)
    else:
        investissement_form = InvestissementForm()

    return render(request, 'projets/ajouter_investissement.html', {
        'projet': projet,
        'investissement_form': investissement_form,
    })


@login_required
def detail_projet(request, projet_id):
    # Récupérer le projet pour l'utilisateur connecté
    projet = get_object_or_404(Projet, id=projet_id, utilisateur=request.user.profile)

    # Récupérer les investissements associés au projet
    investissements = projet.investissement_set.all()

    # Récupérer la prédiction de rendement (s'il y en a une)
    prediction = PredictionRendement.objects.filter(projet=projet).first()

    return render(request, 'projets/detail_projet.html', {
        'projet': projet,
        'investissements': investissements,
        'prediction': prediction,  # Ajout de la prédiction au contexte
    })

@login_required
def liste_projets(request):
    projets_list = Projet.objects.filter(utilisateur=request.user.profile).order_by('-date_lancement')  # Ordonner par date de lancement
    paginator = Paginator(projets_list, 10)  # Affichez 10 projets par page
    page_number = request.GET.get('page')
    projets = paginator.get_page(page_number)
    return render(request, 'projets/liste_projets.html', {'projets': projets})


@login_required
def dashboard(request):
    # Récupérer les projets de l'utilisateur
    projets_user = Projet.objects.filter(utilisateur=request.user.profile)

    # Récupérer les cultures liées aux projets de l'utilisateur
    cultures = ProduitAgricole.objects.filter(id__in=projets_user.values_list('culture_id', flat=True))

    # Calculer la superficie totale des projets de l'utilisateur
    superficie_totale = projets_user.aggregate(Sum('superficie'))['superficie__sum'] or 0

    # Calculer le rendement total estimé des projets de l'utilisateur
    rendement_total = projets_user.aggregate(Sum('rendement_estime'))['rendement_estime__sum'] or 0

    # Identifier les cultures en problème (si l'état est stocké dans ProduitAgricole)
    cultures_en_probleme = cultures.filter(etat='Problème')

    return render(request, 'projets/dashboard.html', {
        'superficie_totale': superficie_totale,
        'rendement_total': rendement_total,
        'cultures_en_probleme': cultures_en_probleme,
        'cultures': cultures,
    })
def get_produit_agricole_details(request):
    produit_id = request.GET.get('produit_id')
    try:
        produit = ProduitAgricole.objects.get(id=produit_id)
        details = f"""
            <strong>Nom :</strong> {produit.nom}<br>
            <strong>Description :</strong> {produit.description}<br>
            <strong>Période de récolte :</strong> {produit.periode_recolte}<br>
            <strong>Rendement moyen :</strong> {produit.rendement_moyen} kg/ha<br>
        """
        return JsonResponse({'details': details})
    except ProduitAgricole.DoesNotExist:
        return JsonResponse({'details': 'Produit agricole non trouvé.'})


def collect_training_data():
    projets = Projet.objects.select_related('culture', 'localite', 'utilisateur').all()
    data = []

    for projet in projets:
        investissement_total = projet.investissement_set.aggregate(models.Sum('cout_par_hectare'))['cout_par_hectare__sum'] or 0
        data.append({
            'superficie': float(projet.superficie),
            'prix_par_kg': float(projet.culture.prix_par_kg or 0),
            'duree_avant_recolte': projet.culture.duree_avant_recolte or 0,
            'type_sol': projet.localite.type_sol,
            'conditions_meteo': projet.localite.conditions_meteo,
            'investissement_total': float(investissement_total),
            'rendement_estime': float(projet.rendement_estime or 0),
        })

    return pd.DataFrame(data)


def entrainer_modele():
    df = collect_training_data()

    # Encoder les variables catégoriques
    df = pd.get_dummies(df, columns=['type_sol', 'conditions_meteo'], drop_first=True)

    X = df.drop('rendement_estime', axis=1)
    y = df['rendement_estime']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Entraîner le modèle
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Évaluer le modèle
    y_pred = model.predict(X_test)
    print(f"Erreur RMSE : {mean_squared_error(y_test, y_pred, squared=False)}")

    # Sauvegarder le modèle
    with open('modele_rendement.pkl', 'wb') as f:
        pickle.dump(model, f)

    return model

import pickle
from django.db.models import Sum

def predire_rendement(projet):
    model = None
    try:
        with open('modele_rendement.pkl', 'rb') as f:
            model = pickle.load(f)
    except (FileNotFoundError, pickle.UnpicklingError) as e:
        logger.error(f"Erreur lors du chargement du modèle : {e}")
        return 0  # Retourne 0 si le modèle ne peut pas être chargé

    investissement_total = projet.investissement_set.aggregate(Sum('cout_par_hectare'))['cout_par_hectare__sum'] or 0

    # Créer un input pour le modèle
    data = {
        'superficie': float(projet.superficie),
        'prix_par_kg': float(projet.culture.prix_par_kg or 0),
        'duree_avant_recolte': projet.culture.duree_avant_recolte or 0,
        'type_sol': projet.localite.type_sol,
        'conditions_meteo': projet.localite.conditions_meteo,
        'investissement_total': float(investissement_total),
    }

    # Encoder les variables catégoriques
    input_data = pd.DataFrame([data])
    input_data = pd.get_dummies(input_data, columns=['type_sol', 'conditions_meteo'], drop_first=True)

    # Assurer la compatibilité avec les colonnes du modèle
    for col in model.feature_names_in_:
        if col not in input_data.columns:
            input_data[col] = 0

    # S'assurer que les colonnes sont dans le bon ordre
    input_data = input_data[model.feature_names_in_]

    # Faire la prédiction
    rendement_pred = model.predict(input_data)[0]
    return rendement_pred

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Projet)
def creer_prediction_rendement(sender, instance, created, **kwargs):
    if created:
        rendement_pred = predire_rendement(instance)
        PredictionRendement.objects.create(projet=instance, rendement_estime=rendement_pred)

@login_required
def generer_prediction(request, projet_id):
    projet = get_object_or_404(Projet, id=projet_id, utilisateur=request.user.profile)

    # Exemple de prédiction simple
    prediction, created = PredictionRendement.objects.get_or_create(
        projet=projet,
        defaults={'rendement_estime': projet.superficie * 100}  # Exemple
    )

    return redirect('detail_projet', projet_id=projet.id)