import json
import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.urls import reverse_lazy
import os
from google import genai
from sklearn.metrics import r2_score, mean_absolute_error
import numpy as np
from Andd_Baayi import settings
from baay.forms import CustomUserCreationForm, ProjetForm, InvestissementForm
from baay.models  import Profile, Projet, ProduitAgricole, PredictionRendement
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.metrics import mean_squared_error
import pickle
from django.db.models import Sum

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



# Créer le client Gemini avec la clé depuis settings
client = genai.Client(api_key=settings.GEMINI_API_KEY)

@csrf_exempt
def ask_chatbot(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            prompt = data.get('message', '')

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )

            return JsonResponse({'response': response.text})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid method'}, status=405)

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
def supprimer_projets(request):
    if request.method == 'POST':
        projets_ids = request.POST.getlist('projets')
        if projets_ids:
            Projet.objects.filter(id__in=projets_ids, utilisateur=request.user.profile).delete()
            messages.success(request, f"{len(projets_ids)} projet(s) supprimé(s) avec succès.")
        else:
            messages.warning(request, "Aucun projet sélectionné.")
    return redirect('liste_projets')

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


# Exemple de vue Django
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    utilisateur = request.user.profile  # Assure-toi que le profil est bien lié via OneToOneField
    projets = Projet.objects.filter(utilisateur=utilisateur)

    superficie_totale = projets.aggregate(Sum('superficie'))['superficie__sum'] or 0
    rendement_total = projets.aggregate(Sum('rendement_estime'))['rendement_estime__sum'] or 0

    context = {
        'projets': projets,
        'superficie_totale': superficie_totale,
        'rendement_total': rendement_total,
    }
    return render(request, 'projets/dashboard.html', context)


def get_produit_agricole_details(request):
    produit_id = request.GET.get('produit_id')
    try:
        produit = ProduitAgricole.objects.get(id=id)
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
        investissement_total = projet.investissement_set.aggregate(Sum('cout_par_hectare'))['cout_par_hectare__sum'] or 0
        data.append({
            'superficie': float(projet.superficie or 0),
            'prix_par_kg': float(projet.culture.prix_par_kg or 0),
            'duree_avant_recolte': projet.culture.duree_avant_recolte or 0,
            'type_sol': projet.localite.type_sol or 'unknown',
            'conditions_meteo': projet.localite.conditions_meteo or 'unknown',
            'investissement_total': float(investissement_total),
            'rendement_estime': float(projet.rendement_estime or 0),
        })

    df = pd.DataFrame(data)
    logger.debug(f"Training data collected: {df.head()}")
    return df

def entrainer_modele():
    df = collect_training_data()
    if df.empty:
        logger.error("Les données d'entraînement sont vides.")
    else:
        logger.info(f"Données d'entraînement collectées : {df.shape[0]} lignes, {df.shape[1]} colonnes.")

    if df.empty:
        logger.error("No data available for training!")
        return None

    df = pd.get_dummies(df, columns=['type_sol', 'conditions_meteo'], drop_first=True)

    X = df.drop('rendement_estime', axis=1)
    y = df['rendement_estime']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    param_grid = {
        'n_estimators': [50, 100, 200],
        'max_depth': [None, 10, 20, 30],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
    }

    model = RandomizedSearchCV(RandomForestRegressor(random_state=42), param_grid, n_iter=10, cv=3, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.best_estimator_.predict(X_test)
    logger.info(f"Model RMSE: {mean_squared_error(y_test, y_pred, squared=False)}")

    with open('modele_rendement.pkl', 'wb') as f:
        pickle.dump(model.best_estimator_, f)

    logger.info("Optimized model saved successfully.")
    return model.best_estimator_


model_cache = None

def get_model():
    global model_cache
    if model_cache is None:
        try:
            with open('modele_rendement.pkl', 'rb') as f:
                model_cache = pickle.load(f)
                logger.debug("Model loaded into cache.")
        except FileNotFoundError:
            logger.error("Le fichier modele_rendement.pkl est introuvable.")
            return None
        except pickle.UnpicklingError:
            logger.error("Erreur lors du chargement du modèle : fichier corrompu.")
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue lors du chargement du modèle : {e}")
            return None
    return model_cache


def predire_rendement(projet):

    model = get_model()
    if model is None:
        return 0


    try:
        with open('modele_rendement.pkl', 'rb') as f:
            model = pickle.load(f)
            logger.debug("Model loaded successfully.")
    except FileNotFoundError:
        logger.error("Le fichier modele_rendement.pkl est introuvable.")
        return 0
    except pickle.UnpicklingError:
        logger.error("Erreur lors du chargement du modèle : fichier corrompu.")
        return 0
    except Exception as e:
        logger.error(f"Erreur inattendue lors du chargement du modèle : {e}")
        return 0

    investissement_total = projet.investissement_set.aggregate(Sum('cout_par_hectare'))['cout_par_hectare__sum'] or 0

    try:
        data = {
            'superficie': float(projet.superficie or 0),
            'prix_par_kg': float(projet.culture.prix_par_kg or 0),
            'duree_avant_recolte': projet.culture.duree_avant_recolte or 0,
            'investissement_total': float(investissement_total),
        }

        sol = f"type_sol_{projet.localite.type_sol or 'unknown'}"
        meteo = f"conditions_meteo_{projet.localite.conditions_meteo or 'unknown'}"

        columns = model.feature_names_in_
        input_data = pd.DataFrame([data], columns=columns).fillna(0)

        if sol in columns:
            input_data[sol] = 1
        if meteo in columns:
            input_data[meteo] = 1

        prediction = model.predict(input_data)[0]
        return prediction

    except KeyError as e:
        logger.error(f"Colonne manquante dans les données d'entrée : {e}")
        return 0
    except Exception as e:
        logger.error(f"Erreur lors de la prédiction : {e}")
        return 0

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Projet)
def creer_prediction_rendement(sender, instance, created, **kwargs):
    if created:
        logger.debug(f"Signal triggered for project {instance.id}")
        rendement_pred = predire_rendement(instance)
        PredictionRendement.objects.create(projet=instance, rendement_estime=rendement_pred)
        
@login_required
def generer_prediction(request, projet_id):
    projet = get_object_or_404(Projet, id=projet_id, utilisateur=request.user.profile)

    rendement_pred = predire_rendement(projet)
    prediction, created = PredictionRendement.objects.get_or_create(
        projet=projet,
        defaults={'rendement_estime': rendement_pred}
    )

    if not created:
        prediction.rendement_estime = rendement_pred
        prediction.save()

    messages.success(request, "La prédiction a été générée avec succès.")
    return redirect('detail_projet', projet_id=projet.id)

def evaluer_modele(model, X_test, y_test):
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    logger.info(f"Model Evaluation - RMSE: {rmse:.2f}, R²: {r2:.2f}, MAE: {mae:.2f}")
    return {'rmse': rmse, 'r2': r2, 'mae': mae}


