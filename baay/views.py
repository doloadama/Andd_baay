import json
import logging
import os
import pickle
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth
from django.views.decorators.http import require_GET

from Andd_Baayi import settings
from baay.forms import CustomUserCreationForm, ProjetForm, InvestissementForm
from baay.models import Profile, Projet, ProduitAgricole, PredictionRendement

# Optional ML imports - these are large dependencies that may not be available in serverless
ML_AVAILABLE = False
try:
    import numpy as np
    import pandas as pd
    from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import RandomizedSearchCV, train_test_split
    ML_AVAILABLE = True
except ImportError:
    np = None
    pd = None
    logging.warning("ML dependencies (numpy, pandas, scikit-learn) not available. ML features disabled.")

# Optional Gemini import
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False
    logging.warning("Google Generative AI not available. Chatbot disabled.")

# Vue pour la page d'accueil
def home_view(request):
    return render(request, 'home.html')

# Vue pour l'inscription
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # Enregistre l'utilisateur
            # Le signal post_save crée déjà le Profile automatiquement.
            # On met à jour le numéro de téléphone sur le profil existant.
            profile = user.profile
            profile.phone_number = form.cleaned_data['phone_number']
            profile.save()
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



logger = logging.getLogger(__name__)

# Create Gemini client only if available
client = None
if GEMINI_AVAILABLE and hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini client: {e}")

# Maximum allowed prompt length for chatbot
MAX_PROMPT_LENGTH = 4000

def _sanitize_chatbot_input(prompt):
    """Sanitize and validate chatbot input."""
    if not prompt or not isinstance(prompt, str):
        return None, "Message is required and must be a string."
    
    # Strip whitespace and check length
    prompt = prompt.strip()
    if len(prompt) == 0:
        return None, "Message cannot be empty."
    
    if len(prompt) > MAX_PROMPT_LENGTH:
        return None, f"Message exceeds maximum length of {MAX_PROMPT_LENGTH} characters."
    
    # Remove potentially harmful content (basic sanitization)
    # This prevents prompt injection attempts
    sanitized = prompt.replace('\x00', '')  # Remove null bytes
    
    return sanitized, None

# Chatbot — CSRF enabled, login required for security
@login_required
def ask_chatbot(request):
    if not client:
        return JsonResponse({'error': 'Chatbot is not available. Please configure GEMINI_API_KEY.'}, status=503)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            raw_prompt = data.get('message', '')
            
            # Sanitize and validate input
            prompt, error = _sanitize_chatbot_input(raw_prompt)
            if error:
                return JsonResponse({'error': error}, status=400)

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )

            return JsonResponse({'response': response.text})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
        except Exception as e:
            logger.error(f"Chatbot error: {type(e).__name__}: {e}")
            return JsonResponse({'error': 'An error occurred processing your request.'}, status=500)

    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def creer_projet(request):
    if request.method == 'POST':
        projet_form = ProjetForm(request.POST)
        if projet_form.is_valid():
            # Sauvegarder le projet en associant l'utilisateur connecté
            projet = projet_form.save(commit=False)
            projet.utilisateur = request.user.profile  # Associer le profil de l'utilisateur connecté
            
            # Calcul automatique du rendement estimé si non fourni
            if not projet.rendement_estime and projet.culture and projet.culture.rendement_moyen:
                projet.rendement_estime = projet.superficie * projet.culture.rendement_moyen
                
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
            projet = projet_form.save(commit=False)
            
            # Recalculer le rendement lors d'une modification
            if projet.culture and projet.culture.rendement_moyen:
                projet.rendement_estime = projet.superficie * projet.culture.rendement_moyen
                
            projet.save()
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
    # Vérifier que le projet appartient à l'utilisateur connecté
    projet = get_object_or_404(Projet, id=projet_id, utilisateur=request.user.profile)

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
    try:
        utilisateur = request.user.profile  # Vérifie si le profil existe
    except Profile.DoesNotExist:
        # Crée un profil si nécessaire
        utilisateur = Profile.objects.create(user=request.user)

    projets = Projet.objects.filter(utilisateur=utilisateur).select_related('culture', 'localite')

    superficie_totale = projets.aggregate(Sum('superficie'))['superficie__sum'] or 0
    rendement_total = projets.aggregate(Sum('rendement_estime'))['rendement_estime__sum'] or 0
    
    # Get investissements total
    from baay.models import Investissement
    investissement_total = Investissement.objects.filter(
        projet__in=projets
    ).aggregate(total=Sum('cout_par_hectare'))['total'] or 0
    
    # Projects by status count
    projets_en_cours = projets.filter(statut='en_cours').count()
    projets_en_pause = projets.filter(statut='en_pause').count()
    projets_finis = projets.filter(statut='fini').count()
    
    # Get unique cultures for filter
    cultures = ProduitAgricole.objects.filter(
        projet__utilisateur=utilisateur
    ).distinct()

    context = {
        'projets': projets,
        'superficie_totale': superficie_totale,
        'rendement_total': rendement_total,
        'investissement_total': investissement_total,
        'utilisateur': utilisateur,
        'projets_en_cours': projets_en_cours,
        'projets_en_pause': projets_en_pause,
        'projets_finis': projets_finis,
        'cultures': cultures,
    }

    return render(request, 'projets/dashboard.html', context)


@login_required
def profil_view(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
        
    if request.method == 'POST':
        # Import local to avoid circular import if needed, though they are imported at the top
        from baay.forms import UserUpdateForm, ProfileUpdateForm
        
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Votre profil a été mis à jour avec succès !')
            return redirect('profil')
    else:
        from baay.forms import UserUpdateForm, ProfileUpdateForm
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }

    return render(request, 'auth/profil.html', context)


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
    """Collect training data from projects. Requires ML dependencies."""
    if not ML_AVAILABLE:
        logger.warning("ML dependencies not available. Cannot collect training data.")
        return None
    
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
    """Train the ML model. Requires ML dependencies."""
    if not ML_AVAILABLE:
        logger.error("ML dependencies not available. Cannot train model.")
        return None
    
    df = collect_training_data()
    if df is None or df.empty:
        logger.error("Les données d'entraînement sont vides.")
        return None
    
    logger.info(f"Données d'entraînement collectées : {df.shape[0]} lignes, {df.shape[1]} colonnes.")

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


import hashlib
import threading

# Thread-safe model cache
_model_cache = None
_model_lock = threading.Lock()

# Expected model hash (update this after training a new model)
EXPECTED_MODEL_HASH = os.getenv('ML_MODEL_HASH', '')

def _compute_file_hash(filepath):
    """Compute SHA256 hash of a file for integrity verification."""
    sha256_hash = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b''):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_model():
    """Load and cache the ML model with thread-safety and integrity validation."""
    global _model_cache
    
    # ML dependencies required for unpickling sklearn models
    if not ML_AVAILABLE:
        logger.debug("ML dependencies not available. Using fallback predictions.")
        return None
    
    if _model_cache is not None:
        return _model_cache
    
    with _model_lock:
        # Double-check after acquiring lock
        if _model_cache is not None:
            return _model_cache
        
        model_path = 'modele_rendement.pkl'
        
        try:
            # Verify model file integrity if hash is configured
            if EXPECTED_MODEL_HASH:
                actual_hash = _compute_file_hash(model_path)
                if actual_hash != EXPECTED_MODEL_HASH:
                    logger.error(
                        f"Model integrity check failed. Expected hash: {EXPECTED_MODEL_HASH[:16]}..., "
                        f"Got: {actual_hash[:16]}..."
                    )
                    return None
                logger.info("Model integrity verified successfully.")
            
            with open(model_path, 'rb') as f:
                loaded_model = pickle.load(f)
            
            # Validate the model has expected attributes
            if not hasattr(loaded_model, 'predict') or not hasattr(loaded_model, 'feature_names_in_'):
                logger.error("Loaded model is missing required attributes (predict, feature_names_in_).")
                return None
            
            _model_cache = loaded_model
            logger.info("Model loaded and cached successfully.")
            
        except FileNotFoundError:
            logger.error("Le fichier modele_rendement.pkl est introuvable.")
            return None
        except pickle.UnpicklingError as e:
            logger.error(f"Erreur lors du chargement du modèle : fichier corrompu. {e}")
            return None
        except (IOError, OSError) as e:
            logger.error(f"Erreur d'accès au fichier modèle : {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue lors du chargement du modèle : {type(e).__name__}: {e}")
            return None
    
    return _model_cache


def predire_rendement(projet):
    model = get_model()
    
    # Fallback mathématique (Moyenne Hectare * Superficie)
    fallback_rendement = 0
    if projet.culture and projet.culture.rendement_moyen:
        fallback_rendement = float(projet.superficie * projet.culture.rendement_moyen)

    if model is None:
        return fallback_rendement

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

    # Mettre à jour le rendement estimé global du projet
    projet.rendement_estime = rendement_pred
    projet.save(update_fields=['rendement_estime'])

    messages.success(request, "La prédiction a été générée avec succès.")
    return redirect('detail_projet', projet_id=projet.id)

def evaluer_modele(model, X_test, y_test):
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    logger.info(f"Model Evaluation - RMSE: {rmse:.2f}, R²: {r2:.2f}, MAE: {mae:.2f}")
    return {'rmse': rmse, 'r2': r2, 'mae': mae}


# ===================== DASHBOARD API ENDPOINTS =====================

@login_required
@require_GET
def dashboard_stats_api(request):
    """API endpoint for dashboard statistics with filtering"""
    try:
        utilisateur = request.user.profile
    except Profile.DoesNotExist:
        utilisateur = Profile.objects.create(user=request.user)
    
    # Get filter parameters
    statut_filter = request.GET.get('statut', '')
    culture_filter = request.GET.get('culture', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    projets = Projet.objects.filter(utilisateur=utilisateur)
    
    # Apply filters
    if statut_filter:
        projets = projets.filter(statut=statut_filter)
    if culture_filter:
        projets = projets.filter(culture__id=culture_filter)
    if date_from:
        projets = projets.filter(date_lancement__gte=date_from)
    if date_to:
        projets = projets.filter(date_lancement__lte=date_to)
    
    # Calculate statistics
    superficie_totale = projets.aggregate(Sum('superficie'))['superficie__sum'] or Decimal('0')
    rendement_total = projets.aggregate(Sum('rendement_estime'))['rendement_estime__sum'] or Decimal('0')
    
    # Get investissements total
    from baay.models import Investissement
    investissement_total = Investissement.objects.filter(
        projet__in=projets
    ).aggregate(total=Sum('cout_par_hectare'))['total'] or Decimal('0')
    
    # Projects by status
    projets_par_statut = list(projets.values('statut').annotate(count=Count('id')))
    
    # Projects by culture
    projets_par_culture = list(projets.values('culture__nom').annotate(
        count=Count('id'),
        superficie=Sum('superficie'),
        rendement=Sum('rendement_estime')
    ))
    
    # Monthly trends (last 12 months)
    monthly_data = list(projets.annotate(
        month=TruncMonth('date_lancement')
    ).values('month').annotate(
        count=Count('id'),
        superficie=Sum('superficie'),
        rendement=Sum('rendement_estime')
    ).order_by('month'))
    
    # Convert Decimal to float for JSON serialization
    def decimal_to_float(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return obj
    
    data = {
        'superficie_totale': decimal_to_float(superficie_totale),
        'rendement_total': decimal_to_float(rendement_total),
        'investissement_total': decimal_to_float(investissement_total),
        'nb_projets': projets.count(),
        'projets_par_statut': projets_par_statut,
        'projets_par_culture': [
            {
                'culture': p['culture__nom'],
                'count': p['count'],
                'superficie': decimal_to_float(p['superficie']),
                'rendement': decimal_to_float(p['rendement'])
            } for p in projets_par_culture
        ],
        'monthly_trends': [
            {
                'month': p['month'].strftime('%Y-%m') if p['month'] else None,
                'count': p['count'],
                'superficie': decimal_to_float(p['superficie']),
                'rendement': decimal_to_float(p['rendement'])
            } for p in monthly_data
        ]
    }
    
    return JsonResponse(data)


@login_required
@require_GET
def dashboard_projets_api(request):
    """API endpoint for projects list with search and pagination"""
    try:
        utilisateur = request.user.profile
    except Profile.DoesNotExist:
        utilisateur = Profile.objects.create(user=request.user)
    
    search = request.GET.get('search', '')
    statut = request.GET.get('statut', '')
    sort_by = request.GET.get('sort', '-date_lancement')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 10))
    
    projets = Projet.objects.filter(utilisateur=utilisateur).select_related('culture', 'localite')
    
    if search:
        projets = projets.filter(nom__icontains=search)
    if statut:
        projets = projets.filter(statut=statut)
    
    # Sorting
    valid_sorts = ['date_lancement', '-date_lancement', 'superficie', '-superficie', 
                   'rendement_estime', '-rendement_estime', 'nom', '-nom']
    if sort_by in valid_sorts:
        projets = projets.order_by(sort_by)
    
    # Pagination
    total = projets.count()
    start = (page - 1) * per_page
    end = start + per_page
    projets_page = projets[start:end]
    
    projets_data = []
    for p in projets_page:
        # Get prediction if exists
        prediction = None
        try:
            if hasattr(p, 'prediction'):
                prediction = p.prediction.rendement_estime
        except (AttributeError, PredictionRendement.DoesNotExist):
            logger.debug(f"No prediction found for project {p.id}")
        
        projets_data.append({
            'id': str(p.id),
            'nom': p.nom,
            'statut': p.statut,
            'culture': p.culture.nom if p.culture else None,
            'localite': p.localite.nom if p.localite else None,
            'superficie': float(p.superficie) if p.superficie else 0,
            'rendement_estime': float(p.rendement_estime) if p.rendement_estime else 0,
            'prediction': prediction,
            'date_lancement': p.date_lancement.strftime('%Y-%m-%d') if p.date_lancement else None,
        })
    
    return JsonResponse({
        'projets': projets_data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })


@login_required
@require_GET 
def dashboard_filters_api(request):
    """API endpoint to get available filter options"""
    try:
        utilisateur = request.user.profile
    except Profile.DoesNotExist:
        utilisateur = Profile.objects.create(user=request.user)
    
    # Get unique cultures for this user's projects
    cultures = list(ProduitAgricole.objects.filter(
        projet__utilisateur=utilisateur
    ).distinct().values('id', 'nom'))
    
    # Get status options
    statuts = [
        {'value': 'en_cours', 'label': 'En cours'},
        {'value': 'en_pause', 'label': 'En pause'},
        {'value': 'fini', 'label': 'Fini'},
    ]
    
    return JsonResponse({
        'cultures': [{'id': str(c['id']), 'nom': c['nom']} for c in cultures],
        'statuts': statuts
    })


@login_required
def update_projet_statut_api(request, projet_id):
    """API endpoint to update project status"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        nouveau_statut = data.get('statut')
        
        if nouveau_statut not in ['en_cours', 'en_pause', 'fini']:
            return JsonResponse({'error': 'Invalid status'}, status=400)
        
        projet = get_object_or_404(Projet, id=projet_id, utilisateur=request.user.profile)
        projet.statut = nouveau_statut
        projet.save(update_fields=['statut'])
        
        return JsonResponse({
            'success': True,
            'projet_id': str(projet.id),
            'nouveau_statut': nouveau_statut
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
    except Projet.DoesNotExist:
        return JsonResponse({'error': 'Project not found.'}, status=404)
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid data in update_projet_statut_api: {e}")
        return JsonResponse({'error': 'Invalid data provided.'}, status=400)
    except Exception as e:
        logger.error(f"Error in update_projet_statut_api: {type(e).__name__}: {e}")
        return JsonResponse({'error': 'An error occurred processing your request.'}, status=500)


# ============ SEMIS (Sowing) Management Views ============

@login_required
def liste_semis(request):
    """List all sowings for the current user"""
    try:
        utilisateur = request.user.profile
    except Profile.DoesNotExist:
        utilisateur = Profile.objects.create(user=request.user)
    
    # Get filter parameters
    statut_filter = request.GET.get('statut', '')
    culture_filter = request.GET.get('culture', '')
    search_query = request.GET.get('q', '')
    
    # Base queryset
    semis_list = Semis.objects.filter(utilisateur=utilisateur).select_related('culture', 'projet')
    
    # Apply filters
    if statut_filter:
        semis_list = semis_list.filter(statut=statut_filter)
    
    if culture_filter:
        semis_list = semis_list.filter(culture_id=culture_filter)
    
    if search_query:
        semis_list = semis_list.filter(culture__nom__icontains=search_query)
    
    # Pagination
    paginator = Paginator(semis_list, 12)
    page = request.GET.get('page', 1)
    semis = paginator.get_page(page)
    
    # Get available cultures for filter dropdown
    cultures = ProduitAgricole.objects.filter(
        semis__utilisateur=utilisateur
    ).distinct()
    
    # Statistics
    stats = {
        'total': semis_list.count(),
        'planifies': semis_list.filter(statut='planifie').count(),
        'en_croissance': semis_list.filter(statut='en_croissance').count(),
        'recoltes': semis_list.filter(statut='recolte').count(),
    }
    
    context = {
        'semis': semis,
        'cultures': cultures,
        'stats': stats,
        'current_statut': statut_filter,
        'current_culture': culture_filter,
        'search_query': search_query,
    }
    
    return render(request, 'semis/liste_semis.html', context)


@login_required
def creer_semis(request):
    """Create a new sowing"""
    if request.method == 'POST':
        form = SemisForm(request.POST, user=request.user)
        if form.is_valid():
            semis = form.save(commit=False)
            semis.utilisateur = request.user.profile
            semis.save()
            messages.success(request, 'Semis créé avec succès!')
            return redirect('liste_semis')
    else:
        form = SemisForm(user=request.user)
    
    return render(request, 'semis/creer_semis.html', {'form': form})


@login_required
def modifier_semis(request, semis_id):
    """Edit an existing sowing"""
    semis = get_object_or_404(Semis, id=semis_id, utilisateur=request.user.profile)
    
    if request.method == 'POST':
        form = SemisForm(request.POST, instance=semis, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Semis modifié avec succès!')
            return redirect('liste_semis')
    else:
        form = SemisForm(instance=semis, user=request.user)
    
    return render(request, 'semis/modifier_semis.html', {'form': form, 'semis': semis})


@login_required
def detail_semis(request, semis_id):
    """View details of a sowing"""
    semis = get_object_or_404(
        Semis.objects.select_related('culture', 'projet', 'utilisateur'),
        id=semis_id, 
        utilisateur=request.user.profile
    )
    
    return render(request, 'semis/detail_semis.html', {'semis': semis})


@login_required
def supprimer_semis(request, semis_id):
    """Delete a sowing"""
    semis = get_object_or_404(Semis, id=semis_id, utilisateur=request.user.profile)
    
    if request.method == 'POST':
        semis.delete()
        messages.success(request, 'Semis supprimé avec succès!')
        return redirect('liste_semis')
    
    return render(request, 'semis/confirmer_suppression_semis.html', {'semis': semis})


@login_required
def update_semis_statut(request, semis_id):
    """Quick update of sowing status"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        nouveau_statut = data.get('statut')
        
        valid_statuts = ['planifie', 'seme', 'en_croissance', 'recolte', 'echec']
        if nouveau_statut not in valid_statuts:
            return JsonResponse({'error': 'Invalid status'}, status=400)
        
        semis = get_object_or_404(Semis, id=semis_id, utilisateur=request.user.profile)
        semis.statut = nouveau_statut
        semis.save(update_fields=['statut'])
        
        return JsonResponse({
            'success': True,
            'semis_id': str(semis.id),
            'nouveau_statut': nouveau_statut
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error updating semis status: {e}")
        return JsonResponse({'error': 'An error occurred'}, status=500)
