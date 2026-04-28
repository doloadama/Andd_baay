import json
import logging
import os
import pickle
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q, Sum, Count, Avg
from django.db.models.functions import TruncMonth
from django.views.decorators.http import require_GET, require_POST

from Andd_Baayi import settings
from baay.forms import CustomUserCreationForm, ProjetForm, InvestissementForm, ProjetProduitForm, RendementFinalForm, PlantDetailsForm, FermeForm, MembreFermeForm, DemandeAccesFermeForm, TacheForm, TacheStatutForm
from baay.models import Profile, Projet, ProduitAgricole, PrevisionRecolte, ProjetProduit, Localite, Investissement, Ferme, MembreFerme, DemandeAccesFerme, Tache

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
    from django.contrib.auth import get_user_model
    User = get_user_model()

    context = {
        'stats': {
            'nb_users': User.objects.count(),
            'nb_projets': Projet.objects.count(),
        }
    }

    if request.user.is_authenticated:
        try:
            projets_actifs = Projet.objects.filter(
                utilisateur=request.user.profile, statut='en_cours'
            ).count()
            prochain_semis = Projet.objects.filter(
                utilisateur=request.user.profile
            ).order_by('-date_lancement').first()
            context['projets_actifs'] = projets_actifs
            context['prochain_projet'] = prochain_semis
        except Exception as e:
            logger.error("Erreur home_view", exc_info=True)
            context['projets_actifs'] = 0
            context['prochain_projet'] = None

    return render(request, 'home.html', context)

def _send_confirmation_email(user, request):
    """Send email confirmation link using Django token generator."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    domain = request.get_host()
    protocol = 'https' if request.is_secure() else 'http'
    confirm_url = f"{protocol}://{domain}/confirm-email/{uid}/{token}/"

    subject = "Confirmez votre compte Andd Baay"
    message_text = (
        f"Bonjour {user.first_name or user.username},\n\n"
        f"Merci de votre inscription sur Andd Baay.\n"
        f"Cliquez sur le lien ci-dessous pour activer votre compte :\n\n"
        f"{confirm_url}\n\n"
        f"Si vous n'avez pas créé ce compte, ignorez cet email.\n\n"
        f"L'équipe Andd Baay"
    )
    message_html = (
        f"<p>Bonjour <strong>{user.first_name or user.username}</strong>,</p>"
        f"<p>Merci de votre inscription sur Andd Baay.</p>"
        f"<p><a href='{confirm_url}' style='padding:12px 24px;background:#d4af37;color:#fff;text-decoration:none;border-radius:8px;'>"
        f"Activer mon compte</a></p>"
        f"<p>Si le bouton ne fonctionne pas, copiez ce lien :<br>{confirm_url}</p>"
        f"<p>Si vous n'avez pas créé ce compte, ignorez cet email.</p>"
    )

    from django.core.mail import EmailMultiAlternatives
    email = EmailMultiAlternatives(
        subject=subject,
        body=message_text,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@anddbaay.local'),
        to=[user.email],
    )
    email.attach_alternative(message_html, "text/html")
    email.send()


# Vue pour l'inscription
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Account inactive until email confirmed
            user.save()

            # Update profile phone number
            profile = user.profile
            profile.phone_number = form.cleaned_data['phone_number']
            profile.save()

            # Send confirmation email
            _send_confirmation_email(user, request)

            messages.success(
                request,
                "Inscription réussie ! Un email de confirmation a été envoyé. Cliquez sur le lien pour activer votre compte."
            )
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'auth/register.html', {'form': form})


def confirm_email_view(request, uidb64, token):
    """Activate account after user clicks confirmation link in email."""
    from django.contrib.auth.models import User
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Votre compte est activé ! Vous pouvez maintenant vous connecter.")
        return redirect('login')
    else:
        messages.error(request, "Le lien de confirmation est invalide ou a expiré.")
        return redirect('login')

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Sends a notification email after a successful password reset."""
    template_name = 'auth/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

    def form_valid(self, form):
        user = form.user
        response = super().form_valid(form)

        # Send password change notification email
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string

        domain = self.request.get_host()
        protocol = 'https' if self.request.is_secure() else 'http'
        ctx = {
            'user': user,
            'domain': domain,
            'protocol': protocol,
        }

        subject = "Andd Baay — Votre mot de passe a été modifié"
        text_body = render_to_string('registration/password_change_subject.txt', ctx)
        html_body = render_to_string('registration/password_change_email.html', ctx)

        email = EmailMultiAlternatives(
            subject=subject,
            body=f"Bonjour {user.first_name or user.username},\n\nVotre mot de passe a été modifié avec succès.\n\nSi vous n'êtes pas à l'origine de ce changement, réinitialisez-le immédiatement : {protocol}://{domain}/password_reset/",
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@anddbaay.local'),
            to=[user.email],
        )
        email.attach_alternative(html_body, "text/html")
        email.send()

        return response


# Vue pour la connexion
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if not user.is_active:
                    messages.error(
                        request,
                        "Votre compte n'est pas encore activé. Vérifiez vos emails et cliquez sur le lien de confirmation."
                    )
                    return redirect('login')
                login(request, user)
                messages.success(request, f"Bienvenue, {username} !")
                return redirect('dashboard')
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
    # Use the non-empty auth templates (the registration/ ones were left empty).
    template_name = 'auth/password_reset_form.html'
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
        logger.error(f"Failed to initialize Gemini client: {e}", exc_info=True)

# Maximum allowed prompt length for chatbot
MAX_PROMPT_LENGTH = 4000




# Gemini models to try in order (free tier quota varies per model)
GEMINI_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
]

SYSTEM_PROMPT = """Tu es Baay AI, l'assistant agricole intelligent de la plateforme Andd Baay. 
Tu aides les agriculteurs sénégalais et ouest-africains avec :
- Les cultures locales : mil, sorgho, maïs, arachide, niébé, riz, manioc, igname, coton, sésame, pastèque
- Les techniques de semis, irrigation, fertilisation et récolte adaptées au Sahel
- Les maladies et ravageurs courants (mildiou, chenille légionnaire, etc.)
- La météo agricole et les saisons des pluies (hivernage)
- Les prédictions de rendement et la gestion financière des exploitations
- Les conseils en wolof ou français selon la préférence

Réponds toujours en français (sauf si la question est en wolof). 
Sois précis, pratique et adapté aux réalités locales. 
Limite tes réponses à 300 mots maximum.
Si une question n'est pas agricole, redirige poliment vers ton domaine d'expertise."""

def _sanitize_chatbot_input(prompt):
    """Sanitize and validate chatbot input."""
    if not prompt or not isinstance(prompt, str):
        return None, "Message is required and must be a string."
    prompt = prompt.strip()
    if len(prompt) == 0:
        return None, "Message cannot be empty."
    if len(prompt) > MAX_PROMPT_LENGTH:
        return None, f"Message exceeds maximum length of {MAX_PROMPT_LENGTH} characters."
    sanitized = prompt.replace('\x00', '')
    return sanitized, None

def _call_gemini(full_prompt):
    """Try Gemini models in order, return (text, model_used) or raise last exception."""
    last_error = None
    for model in GEMINI_MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=full_prompt,
            )
            return response.text, model
        except Exception as e:
            logger.error(f"Erreur appel Gemini: {e}", exc_info=True)
            last_error = e
            error_str = str(e)
            # Only retry on quota/rate-limit errors
            if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or 'rate' in error_str.lower():
                logger.warning(f"Model {model} quota exceeded, trying next...")
                continue
            # For other errors (auth, invalid, etc.) fail immediately
            raise
    raise last_error

# Chatbot — CSRF enabled, login required for security
@login_required
def ask_chatbot(request):
    if not client:
        return JsonResponse({
            'error': 'Le chatbot IA est temporairement indisponible. Clé API non configurée.'
        }, status=503)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            raw_prompt = data.get('message', '')
            history = data.get('history', [])  # List of {role, text} from frontend

            # Sanitize input
            prompt, error = _sanitize_chatbot_input(raw_prompt)
            if error:
                logger.warning(f"Chatbot validation error: {error} | Received: '{raw_prompt}' (type: {type(raw_prompt)})")
                return JsonResponse({'error': error}, status=400)

            # Build conversation with system context + history
            conversation_parts = [SYSTEM_PROMPT, "\n\n"]
            for msg in history[-6:]:  # Keep last 6 exchanges to avoid token bloat
                role = msg.get('role', 'user')
                text = msg.get('text', '')[:500]  # Trim history messages
                if role == 'user':
                    conversation_parts.append(f"Utilisateur: {text}")
                else:
                    conversation_parts.append(f"Baay AI: {text}")
            conversation_parts.append(f"\nUtilisateur: {prompt}\nBaay AI:")

            full_prompt = "\n".join(conversation_parts)

            text, model_used = _call_gemini(full_prompt)
            logger.info(f"Chatbot answered via {model_used}")
            return JsonResponse({'response': text, 'model': model_used})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Requête invalide.'}, status=400)
        except Exception as e:
            error_str = str(e)
            logger.error(f"Chatbot error: {type(e).__name__}: {e}", exc_info=True)

            # User-friendly French error messages
            if '403' in error_str or 'permission_denied' in error_str.lower() or 'leaked' in error_str.lower():
                return JsonResponse({
                    'error': '🚨 Votre clé API Gemini a été désactivée par Google car elle a fuité. Veuillez en créer une nouvelle.'
                }, status=403)
            elif '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                if 'limit: 0' in error_str:
                    return JsonResponse({
                        'error': '🚨 Le quota (Free Tier) est désactivé sur cette clé API (limit: 0). Il faut créer une nouvelle clé ou activer la facturation.'
                    }, status=429)
                else:
                    return JsonResponse({
                        'error': '⏳ Le quota de l\'assistant IA est temporairement épuisé. Réessayez dans quelques minutes.'
                    }, status=429)
            elif '401' in error_str or 'API_KEY' in error_str or 'auth' in error_str.lower():
                return JsonResponse({
                    'error': '🔑 Clé API invalide. Contactez l\'administrateur.'
                }, status=503)
            else:
                return JsonResponse({
                    'error': '❌ Une erreur est survenue. Veuillez réessayer.'
                }, status=500)

    return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)


@login_required
def creer_projet(request):
    from django.db.models import Q as _Q
    ferme_id = request.GET.get('ferme')
    from_ferme = None
    if ferme_id:
        from_ferme = get_object_or_404(
            Ferme.objects.filter(
                _Q(proprietaire=request.user.profile) |
                _Q(membres__utilisateur=request.user.profile)
            ).distinct(),
            id=ferme_id
        )

    if request.method == 'POST':
        projet_form = ProjetForm(request.POST, user=request.user, from_ferme=from_ferme)
        if projet_form.is_valid():
            # Sauvegarder le projet en associant l'utilisateur connecte
            projet = projet_form.save(commit=False)
            projet.utilisateur = request.user.profile
            projet.save()

            # Create ProjetProduit entries for each selected product
            produits = projet_form.cleaned_data.get('produits_selection', [])
            superficies_par_produit = projet_form.cleaned_data.get('superficies_par_produit') or {}
            rendement_total = 0
            for produit in produits:
                surf = superficies_par_produit.get(str(produit.id))
                pp = ProjetProduit.objects.create(
                    projet=projet,
                    produit=produit,
                    superficie_allouee=surf,
                )
                # Calculate estimated yield based on product average and allocated area
                if produit.rendement_moyen:
                    if surf:
                        rendement_total += float(surf) * float(produit.rendement_moyen)
                    elif projet.superficie:
                        rendement_total += float(projet.superficie / len(produits)) * float(produit.rendement_moyen)

            # Set backwards compatibility - use first product as main culture
            if produits:
                projet.culture = produits[0]
                if not projet.rendement_estime:
                    projet.rendement_estime = rendement_total

            projet.save()

            messages.success(request, "Le projet a ete cree avec succes.")
            return redirect('liste_projets')
    else:
        initial = {}
        if from_ferme:
            initial['ferme'] = from_ferme.id
            if from_ferme.pays:
                initial['pays'] = from_ferme.pays.id
            if from_ferme.localite:
                initial['localite'] = from_ferme.localite.id
        projet_form = ProjetForm(user=request.user, from_ferme=from_ferme, initial=initial)

    return render(request, 'projets/creer_projet.html', {
        'projet_form': projet_form,
        'produits': ProduitAgricole.objects.all(),
        'from_ferme': from_ferme,
    })


@login_required
def modifier_projet(request, projet_id):
    projet = get_object_or_404(Projet, id=projet_id, utilisateur=request.user.profile)
    rendement_form = None
    plant_details_form = None
    
    # If project is being finished, show the harvest yield form
    show_rendement_form = request.GET.get('finish') == '1' or projet.statut == 'fini'

    if request.method == 'POST':
        projet_form = ProjetForm(request.POST, instance=projet, user=request.user)

        # Handle rendement final form if present
        if 'save_rendement' in request.POST:
            rendement_form = RendementFinalForm(request.POST, projet=projet)
            if rendement_form.is_valid():
                for pp in projet.projet_produits.all():
                    rendement_key = f'rendement_{pp.id}'
                    date_key = f'date_recolte_{pp.id}'
                    if rendement_key in rendement_form.cleaned_data:
                        pp.rendement_final = rendement_form.cleaned_data[rendement_key]
                    if date_key in rendement_form.cleaned_data:
                        pp.date_recolte_effective = rendement_form.cleaned_data[date_key]
                    pp.save()
                messages.success(request, "Les rendements finaux ont ete enregistres.")
                return redirect('detail_projet', projet_id=projet.id)

        elif projet_form.is_valid():
            plant_details_form = PlantDetailsForm(request.POST, request.FILES, projet=projet)
            if plant_details_form.is_valid():
                for pp in projet.projet_produits.all():
                    image_key = f'image_{pp.id}'
                    age_key = f'age_plant_{pp.id}'

                    if image_key in request.FILES:
                        pp.image = request.FILES[image_key]
                    elif image_key in plant_details_form.cleaned_data and plant_details_form.cleaned_data[image_key] is False:
                        if pp.image:
                            pp.image.delete()

                    if age_key in plant_details_form.cleaned_data:
                        pp.age_plant = plant_details_form.cleaned_data[age_key]

                    pp.save()
            else:
                logger.error(f"Erreurs dans plant_details_form : {plant_details_form.errors}")
                # Continue saving the main project even if plant details have errors,
                # but log them so the admin knows.

            projet = projet_form.save(commit=False)
            projet.save()

            # Update products with per-product allocated surface (mirrors creer_projet)
            produits = projet_form.cleaned_data.get('produits_selection', [])
            superficies_par_produit = projet_form.cleaned_data.get('superficies_par_produit') or {}
            existing_produits = set(projet.projet_produits.values_list('produit_id', flat=True))
            new_produits = set(p.id for p in produits)

            # Remove products no longer selected
            for pp in projet.projet_produits.filter(produit_id__in=existing_produits - new_produits):
                pp.delete()

            # Add new products and update existing ones with allocated surface
            for produit in produits:
                surf = superficies_par_produit.get(str(produit.id))
                if produit.id not in existing_produits:
                    ProjetProduit.objects.create(
                        projet=projet,
                        produit=produit,
                        superficie_allouee=surf,
                    )
                elif surf is not None:
                    ProjetProduit.objects.filter(projet=projet, produit=produit).update(
                        superficie_allouee=surf,
                    )

            # Update backwards compatibility culture field
            if produits:
                projet.culture = produits[0]
                projet.save()

            messages.success(request, "Le projet a ete modifie avec succes.")
            return redirect('detail_projet', projet_id=projet.id)
        else:
            # Form invalid — preserve plant_details_form with POST data so the
            # template can re-render submitted values and field errors.
            plant_details_form = PlantDetailsForm(request.POST, request.FILES, projet=projet)
            logger.error(f"Erreurs dans projet_form : {projet_form.errors}")
    else:
        projet_form = ProjetForm(instance=projet, user=request.user)
        plant_details_form = PlantDetailsForm(projet=projet)
        if show_rendement_form:
            rendement_form = RendementFinalForm(projet=projet)

    plants_data = []
    if plant_details_form:
        for pp in projet.projet_produits.all():
            plants_data.append({
                'nom': pp.produit.nom,
                'image_field': plant_details_form[f'image_{pp.id}'],
                'age_field': plant_details_form[f'age_plant_{pp.id}']
            })

    return render(request, 'projets/modifier_projet.html', {
        'projet_form': projet_form,
        'projet': projet,
        'rendement_form': rendement_form,
        'show_rendement_form': show_rendement_form,
        'plant_details_form': plant_details_form,
        'plants_data': plants_data,
        'produits': ProduitAgricole.objects.all(),
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
    # Recuperer le projet pour l'utilisateur connecte
    projet = get_object_or_404(Projet, id=projet_id, utilisateur=request.user.profile)

    # Recuperer les investissements associes au projet
    investissements = projet.investissement_set.all()

    # Recuperer la prediction de rendement (s'il y en a une)
    prediction = PrevisionRecolte.objects.filter(projet=projet).first()
    
    # Recuperer les produits du projet
    projet_produits = projet.projet_produits.select_related('produit').all()
    
    # Pre-calculate photos
    plant_photos = []
    for pp in projet_produits:
        if pp.image:
            plant_photos.append({
                'url': pp.image.url,
                'title': pp.produit.nom,
                'subtitle': f"Age: {pp.age_plant} jours" if pp.age_plant else ""
            })
            
    if projet.culture:
        for photo in projet.culture.photos.all():
            try:
                plant_photos.append({
                    'url': photo.image.url,
                    'title': projet.culture.nom,
                    'subtitle': photo.description or ""
                })
            except Exception as e:
                logger.error("Erreur récupération photo", exc_info=True)
                pass

    return render(request, 'projets/detail_projet.html', {
        'projet': projet,
        'investissements': investissements,
        'prediction': prediction,
        'projet_produits': projet_produits,
        'plant_photos': plant_photos,
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
        utilisateur = request.user.profile
    except Profile.DoesNotExist:
        utilisateur = Profile.objects.create(user=request.user)

    # --- Dispatch selon le rôle primaire ---
    # Si l'utilisateur n'est propriétaire d'aucune ferme, on l'oriente vers
    # un dashboard adapté à son rôle le plus élevé parmi ses adhésions.
    est_proprietaire = Ferme.objects.filter(proprietaire=utilisateur).exists()
    if not est_proprietaire:
        memberships = MembreFerme.objects.filter(utilisateur=utilisateur).select_related('ferme')
        roles = {m.role for m in memberships}
        if not roles:
            # Aucun rôle : page neutre via le dashboard global standard
            pass
        elif 'manager' in roles:
            return _dashboard_manager(request, utilisateur, memberships)
        elif 'technicien' in roles:
            return _dashboard_technicien(request, utilisateur, memberships)
        elif roles == {'ouvrier'}:
            return _dashboard_ouvrier(request, utilisateur, memberships)

    # --- Base querysets ---
    user_fermes = Ferme.objects.filter(
        Q(proprietaire=utilisateur) | Q(membres__utilisateur=utilisateur)
    ).distinct().prefetch_related('membres').order_by('nom')

    # Optional farm filter from GET
    selected_ferme_id = request.GET.get('ferme')
    selected_ferme = None
    if selected_ferme_id:
        try:
            selected_ferme = user_fermes.get(id=selected_ferme_id)
        except Ferme.DoesNotExist:
            pass

    # Projects queryset (optionally filtered by farm)
    projets_qs = Projet.objects.filter(utilisateur=utilisateur).select_related(
        'culture', 'localite', 'ferme'
    ).prefetch_related('projet_produits__produit')
    if selected_ferme:
        projets_qs = projets_qs.filter(ferme=selected_ferme)

    # Apply existing filters
    statut_filter = request.GET.get('statut')
    if statut_filter:
        projets_qs = projets_qs.filter(statut=statut_filter)
    culture_filter = request.GET.get('culture')
    if culture_filter:
        projets_qs = projets_qs.filter(culture__id=culture_filter)
    date_from = request.GET.get('date_from')
    if date_from:
        projets_qs = projets_qs.filter(date_lancement__gte=date_from)
    date_to = request.GET.get('date_to')
    if date_to:
        projets_qs = projets_qs.filter(date_lancement__lte=date_to)

    # --- Aggregates ---
    superficie_totale = projets_qs.aggregate(Sum('superficie'))['superficie__sum'] or 0
    rendement_total = projets_qs.aggregate(Sum('rendement_estime'))['rendement_estime__sum'] or 0
    investissements = Investissement.objects.filter(projet__in=projets_qs)
    investissement_total = sum(
        inv.calculer_investissement_total() for inv in investissements
    ) or 0

    projets_en_cours = projets_qs.filter(statut='en_cours').count()
    projets_en_pause = projets_qs.filter(statut='en_pause').count()
    projets_finis = projets_qs.filter(statut='fini').count()
    total_count = projets_qs.count()
    completion_rate = round((projets_finis / total_count) * 100) if total_count else 0

    # --- Farm-level aggregates ---
    nombre_fermes = user_fermes.count()
    total_membres = MembreFerme.objects.filter(ferme__in=user_fermes).count()

    fermes_data = []
    for ferme in user_fermes:
        f_projets = Projet.objects.filter(ferme=ferme, utilisateur=utilisateur)
        f_projets_actifs = f_projets.filter(statut='en_cours').count()
        f_superficie_ferme = ferme.superficie_totale or 0
        f_superficie_utilisee = f_projets.filter(statut='en_cours').aggregate(s=Sum('superficie'))['s'] or 0
        f_membres = ferme.membres.count()
        f_utilisation = round((f_superficie_utilisee / f_superficie_ferme) * 100, 1) if f_superficie_ferme else 0
        fermes_data.append({
            'ferme': ferme,
            'projets_count': f_projets.count(),
            'projets_actifs': f_projets_actifs,
            'superficie_ferme': f_superficie_ferme,
            'superficie_utilisee': f_superficie_utilisee,
            'membres_count': f_membres + 1,
            'utilisation_pct': f_utilisation,
        })

    # --- Global indicators ---
    projets_total_global = Projet.objects.filter(utilisateur=utilisateur).count()
    avg_projets_par_ferme = round(projets_total_global / nombre_fermes, 1) if nombre_fermes else 0
    fermes_inactives = sum(1 for fd in fermes_data if fd['projets_actifs'] == 0)
    fermes_chart_data = [
        {
            'id': str(fd['ferme'].id),
            'nom': fd['ferme'].nom,
            'utilisation_pct': float(fd['utilisation_pct'] or 0),
            'superficie_ferme': float(fd['superficie_ferme'] or 0),
        }
        for fd in fermes_data
    ]

    # Farm-specific indicators
    if selected_ferme:
        f_proj = Projet.objects.filter(ferme=selected_ferme, utilisateur=utilisateur)
        f_sup = selected_ferme.superficie_totale or 0
        f_sup_u = f_proj.filter(statut='en_cours').aggregate(s=Sum('superficie'))['s'] or 0
        f_util = round((f_sup_u / f_sup) * 100, 1) if f_sup else 0
        f_mem = selected_ferme.membres.count() + 1
        f_rend = f_proj.aggregate(Sum('rendement_estime'))['rendement_estime__sum'] or 0
    else:
        f_sup = f_sup_u = f_util = f_mem = f_rend = 0

    cultures = ProduitAgricole.objects.filter(projet__utilisateur=utilisateur).distinct()
    localites = Localite.objects.all().order_by('nom')

    context = {
        'projets': projets_qs,
        'superficie_totale': superficie_totale,
        'rendement_total': rendement_total,
        'investissement_total': investissement_total,
        'utilisateur': utilisateur,
        'projets_en_cours': projets_en_cours,
        'projets_en_pause': projets_en_pause,
        'projets_finis': projets_finis,
        'completion_rate': completion_rate,
        'cultures': cultures,
        'localites': localites,
        'fermes': user_fermes,
        'selected_ferme': selected_ferme,
        'fermes_data': fermes_data,
        'nombre_fermes': nombre_fermes,
        'total_membres': total_membres,
        'avg_projets_par_ferme': avg_projets_par_ferme,
        'fermes_inactives': fermes_inactives,
        'fermes_chart_data_json': json.dumps(locals().get('fermes_chart_data', [])),
        'ferme_superficie': f_sup,
        'ferme_superficie_utilisee': f_sup_u,
        'ferme_utilisation': f_util,
        'ferme_membres': f_mem,
        'ferme_rendement': f_rend,
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
            logger.error(f"Erreur inattendue lors du chargement du modèle : {type(e).__name__}: {e}", exc_info=True)
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
        logger.error(f"Erreur lors de la prédiction : {e}", exc_info=True)
        return 0



        
@login_required
def generer_prediction(request, projet_id):
    projet = get_object_or_404(Projet, id=projet_id, utilisateur=request.user.profile)
    from baay.services import estimer_rendement_ia

    projet_produits = projet.projet_produits.all()
    if not projet_produits:
        messages.warning(request, "Aucun produit associé à ce projet pour générer une prédiction.")
        return redirect('detail_projet', projet_id=projet.id)

    total_min = 0
    total_max = 0
    confiance_sum = 0
    latest_date_recolte = None
    
    for pp in projet_produits:
        res = estimer_rendement_ia(pp)
        total_min += res['min']
        total_max += res['max']
        confiance_sum += res['confiance']
        if res['date_recolte_prevue']:
            if not latest_date_recolte or res['date_recolte_prevue'] > latest_date_recolte:
                latest_date_recolte = res['date_recolte_prevue']
    
    avg_confiance = confiance_sum / projet_produits.count()
    
    prediction, created = PrevisionRecolte.objects.get_or_create(projet=projet)
    prediction.rendement_estime_min = total_min
    prediction.rendement_estime_max = total_max
    prediction.indice_confiance = avg_confiance
    prediction.date_recolte_prevue = latest_date_recolte
    prediction.save()

    # Mettre à jour le rendement estimé global du projet (moyenne pour compatibilité)
    projet.rendement_estime = (total_min + total_max) / 2
    projet.save(update_fields=['rendement_estime'])

    messages.success(request, "La prédiction a été générée avec succès (Smart Engine).")
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
    """API endpoint for dashboard statistics with filtering (including ferme)"""
    from django.db.models import Q
    try:
        utilisateur = request.user.profile
    except Profile.DoesNotExist:
        utilisateur = Profile.objects.create(user=request.user)
    
    # Get filter parameters
    ferme_filter = request.GET.get('ferme', '')
    statut_filter = request.GET.get('statut', '')
    culture_filter = request.GET.get('culture', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Resolve selected farm
    user_fermes = Ferme.objects.filter(
        Q(proprietaire=utilisateur) | Q(membres__utilisateur=utilisateur)
    ).distinct().prefetch_related('membres')
    selected_ferme = None
    if ferme_filter:
        try:
            selected_ferme = user_fermes.get(id=ferme_filter)
        except Ferme.DoesNotExist:
            pass

    projets = Projet.objects.filter(utilisateur=utilisateur).select_related('culture', 'localite', 'ferme')
    if selected_ferme:
        projets = projets.filter(ferme=selected_ferme)
    
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
    
    # Get investissements total (cout_par_hectare * superficie + autres_frais)
    investissements = Investissement.objects.filter(projet__in=projets)
    investissement_total = sum(
        inv.calculer_investissement_total() for inv in investissements
    ) or Decimal('0')
    
    # Projects by status
    projets_par_statut = list(projets.values('statut').annotate(count=Count('id')))
    
    projets_en_cours = projets.filter(statut='en_cours').count()
    projets_en_pause = projets.filter(statut='en_pause').count()
    projets_finis = projets.filter(statut='fini').count()
    total_count = projets.count()
    completion_rate = round((projets_finis / total_count) * 100) if total_count else 0

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

    # Farm-level aggregates
    nombre_fermes = user_fermes.count()
    total_membres = MembreFerme.objects.filter(ferme__in=user_fermes).count()

    fermes_data = []
    for ferme in user_fermes.order_by('nom'):
        f_projets = Projet.objects.filter(ferme=ferme, utilisateur=utilisateur)
        f_projets_actifs = f_projets.filter(statut='en_cours').count()
        f_superficie_ferme = float(ferme.superficie_totale or 0)
        f_superficie_utilisee = float(f_projets.filter(statut='en_cours').aggregate(s=Sum('superficie'))['s'] or 0)
        f_membres = ferme.membres.count()
        f_utilisation = round((f_superficie_utilisee / f_superficie_ferme) * 100, 1) if f_superficie_ferme else 0
        fermes_data.append({
            'id': str(ferme.id),
            'nom': ferme.nom,
            'projets_count': f_projets.count(),
            'projets_actifs': f_projets_actifs,
            'superficie_ferme': f_superficie_ferme,
            'superficie_utilisee': f_superficie_utilisee,
            'membres_count': f_membres + 1,
            'utilisation_pct': f_utilisation,
        })

    fermes_inactives = sum(1 for fd in fermes_data if fd['projets_actifs'] == 0)

    # Farm-specific KPIs when a farm is selected
    ferme_kpis = None
    if selected_ferme:
        f_proj = Projet.objects.filter(ferme=selected_ferme, utilisateur=utilisateur)
        f_sup = float(selected_ferme.superficie_totale or 0)
        f_sup_u = float(f_proj.filter(statut='en_cours').aggregate(s=Sum('superficie'))['s'] or 0)
        f_util = round((f_sup_u / f_sup) * 100, 1) if f_sup else 0
        f_mem = selected_ferme.membres.count() + 1
        f_rend = float(f_proj.aggregate(Sum('rendement_estime'))['rendement_estime__sum'] or 0)
        ferme_kpis = {
            'id': str(selected_ferme.id),
            'nom': selected_ferme.nom,
            'description': selected_ferme.description or '',
            'localite': selected_ferme.localite.nom if selected_ferme.localite else '',
            'pays': selected_ferme.pays.nom if selected_ferme.pays else '',
            'superficie': f_sup,
            'superficie_utilisee': f_sup_u,
            'utilisation': f_util,
            'membres': f_mem,
            'rendement': f_rend,
        }

    # Projects list for DOM update
    projets_list = []
    for p in projets:
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

    data = {
        'superficie_totale': decimal_to_float(superficie_totale),
        'rendement_total': decimal_to_float(rendement_total),
        'investissement_total': decimal_to_float(investissement_total),
        'nb_projets': total_count,
        'projets_en_cours': projets_en_cours,
        'projets_en_pause': projets_en_pause,
        'projets_finis': projets_finis,
        'completion_rate': completion_rate,
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
        ],
        'nombre_fermes': nombre_fermes,
        'total_membres': total_membres,
        'fermes_data': fermes_data,
        'fermes_inactives': fermes_inactives,
        'selected_ferme': ferme_kpis,
        'projets_list': projets_list,
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
            if hasattr(p, 'prevision'):
                prediction = p.prevision.rendement_estime_min
        except (AttributeError, PrevisionRecolte.DoesNotExist):
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
        logger.error(f"Error in update_projet_statut_api: {type(e).__name__}: {e}", exc_info=True)
        return JsonResponse({'error': 'An error occurred processing your request.'}, status=500)


@login_required
def api_projet_creer(request):
    """API endpoint for quick project creation from the dashboard modal."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        utilisateur = request.user.profile
    except Profile.DoesNotExist:
        utilisateur = Profile.objects.create(user=request.user)

    try:
        nom = request.POST.get('nom', '').strip()
        culture_id = request.POST.get('culture')
        superficie = request.POST.get('superficie')
        localite_id = request.POST.get('localite')
        date_lancement = request.POST.get('date_lancement')
        ferme_id = request.POST.get('ferme')

        if not all([nom, culture_id, superficie, localite_id, date_lancement, ferme_id]):
            return JsonResponse({'error': 'Tous les champs obligatoires doivent être remplis.'}, status=400)

        culture = get_object_or_404(ProduitAgricole, id=culture_id)
        localite = get_object_or_404(Localite, id=localite_id)
        ferme = Ferme.objects.filter(
            models.Q(proprietaire=utilisateur) | models.Q(membres__utilisateur=utilisateur)
        ).filter(id=ferme_id).first()
        if not ferme:
            return JsonResponse({'error': 'Ferme introuvable ou accès refusé.'}, status=403)

        projet = Projet.objects.create(
            nom=nom,
            ferme=ferme,
            culture=culture,
            superficie=superficie,
            localite=localite,
            date_lancement=date_lancement,
            utilisateur=utilisateur,
            statut='en_cours',
        )

        return JsonResponse({
            'success': True,
            'project_id': str(projet.id),
            'message': 'Projet créé avec succès.'
        })
    except Exception as e:
        logger.error(f"Error in api_projet_creer: {type(e).__name__}: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_projet_bulk_delete(request):
    """API endpoint for bulk project deletion."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        if not ids:
            return JsonResponse({'error': 'Aucun identifiant fourni.'}, status=400)

        utilisateur = request.user.profile
        deleted, _ = Projet.objects.filter(
            id__in=ids,
            utilisateur=utilisateur
        ).delete()

        return JsonResponse({
            'success': True,
            'deleted_count': deleted
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
    except Exception as e:
        logger.error(f"Error in api_projet_bulk_delete: {type(e).__name__}: {e}", exc_info=True)
        return JsonResponse({'error': 'An error occurred processing your request.'}, status=500)


# ============ SEMIS (Sowing/Products) Management Views ============
# Now integrated with projects - semis are managed as products within projects

@login_required
def liste_semis(request):
    """List all project products (sowings) for the current user"""
    try:
        utilisateur = request.user.profile
    except Profile.DoesNotExist:
        utilisateur = Profile.objects.create(user=request.user)
    
    # Get filter parameters
    statut_filter = request.GET.get('statut', '')
    culture_filter = request.GET.get('culture', '')
    search_query = request.GET.get('q', '')
    
    # Base queryset - get all products in user's projects
    projet_produits = ProjetProduit.objects.filter(
        projet__utilisateur=utilisateur
    ).select_related('produit', 'projet')
    
    # Apply filters
    if statut_filter:
        projet_produits = projet_produits.filter(projet__statut=statut_filter)
    
    if culture_filter:
        projet_produits = projet_produits.filter(produit_id=culture_filter)
    
    if search_query:
        projet_produits = projet_produits.filter(produit__nom__icontains=search_query)
    
    # Pagination
    paginator = Paginator(projet_produits, 12)
    page = request.GET.get('page', 1)
    semis = paginator.get_page(page)
    
    # Get available cultures for filter dropdown
    cultures = ProduitAgricole.objects.filter(
        projet_produits__projet__utilisateur=utilisateur
    ).distinct()
    
    # Statistics
    stats = {
        'total': projet_produits.count(),
        'en_cours': projet_produits.filter(projet__statut='en_cours').count(),
        'en_pause': projet_produits.filter(projet__statut='en_pause').count(),
        'finis': projet_produits.filter(projet__statut='fini').count(),
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
    """Redirect to create project - products are now added within projects"""
    messages.info(request, "Les semis sont maintenant geres au niveau des projets. Creez un nouveau projet pour ajouter des produits.")
    return redirect('creer_projet')


@login_required
def modifier_semis(request, semis_id):
    """Edit a project product's sowing/harvest details"""
    projet_produit = get_object_or_404(
        ProjetProduit, 
        id=semis_id, 
        projet__utilisateur=request.user.profile
    )
    
    if request.method == 'POST':
        form = ProjetProduitForm(request.POST, instance=projet_produit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Informations mises a jour avec succes!')
            return redirect('detail_projet', projet_id=projet_produit.projet.id)
    else:
        form = ProjetProduitForm(instance=projet_produit)
    
    return render(request, 'semis/modifier_semis.html', {
        'form': form, 
        'semis': projet_produit,
        'projet_produit': projet_produit
    })


@login_required
def detail_semis(request, semis_id):
    """View details of a project product"""
    projet_produit = get_object_or_404(
        ProjetProduit.objects.select_related('produit', 'projet', 'projet__utilisateur'),
        id=semis_id, 
        projet__utilisateur=request.user.profile
    )
    
    return render(request, 'semis/detail_semis.html', {
        'semis': projet_produit,
        'projet_produit': projet_produit
    })


@login_required
def supprimer_semis(request, semis_id):
    """Remove a product from a project"""
    projet_produit = get_object_or_404(
        ProjetProduit, 
        id=semis_id, 
        projet__utilisateur=request.user.profile
    )
    projet_id = projet_produit.projet.id
    
    if request.method == 'POST':
        projet_produit.delete()
        messages.success(request, 'Produit retire du projet avec succes!')
        return redirect('detail_projet', projet_id=projet_id)
    
    return render(request, 'semis/confirmer_suppression_semis.html', {
        'semis': projet_produit,
        'projet_produit': projet_produit
    })


@login_required
def update_semis_statut(request, semis_id):
    """Quick update - redirects to project status since products inherit project status"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        projet_produit = get_object_or_404(
            ProjetProduit, 
            id=semis_id, 
            projet__utilisateur=request.user.profile
        )
        
        # Return project status info
        return JsonResponse({
            'success': True,
            'projet_produit_id': str(projet_produit.id),
            'projet_statut': projet_produit.projet.statut,
            'message': 'Le statut est gere au niveau du projet'
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in update_semis_statut: {e}", exc_info=True)
        return JsonResponse({'error': 'An error occurred'}, status=500)


# ===== FERME VIEWS =====

@login_required
def liste_fermes(request):
    """List all farms the user owns or is a member of."""
    profile = request.user.profile
    fermes_proprietaire = Ferme.objects.filter(proprietaire=profile).select_related('pays', 'localite').prefetch_related('membres__utilisateur__user')
    fermes_membre = Ferme.objects.filter(membres__utilisateur=profile).select_related('pays', 'localite').prefetch_related('membres__utilisateur__user').distinct()
    return render(request, 'fermes/liste_fermes.html', {
        'fermes_proprietaire': fermes_proprietaire,
        'fermes_membre': fermes_membre,
    })


@login_required
def creer_ferme(request):
    if request.method == 'POST':
        form = FermeForm(request.POST)
        if form.is_valid():
            ferme = form.save(commit=False)
            ferme.proprietaire = request.user.profile
            ferme.save()
            messages.success(request, "Fermé créée avec succès.")
            return redirect('detail_ferme', ferme_id=ferme.id)
    else:
        form = FermeForm()
    return render(request, 'fermes/creer_ferme.html', {'form': form})


@login_required
def detail_ferme(request, ferme_id):
    ferme = get_object_or_404(Ferme, id=ferme_id)
    is_proprietaire = ferme.proprietaire == request.user.profile
    membership = ferme.membres.filter(utilisateur=request.user.profile).first()
    is_membre = membership is not None
    can_manage_members = is_proprietaire or (
        membership is not None and membership.peut_gerer_membres
    )
    if not is_proprietaire and not is_membre:
        messages.error(request, "Vous n'avez pas accès à cette ferme.")
        return redirect('liste_fermes')

    projets = ferme.projets.select_related('culture', 'localite')
    membres = ferme.membres.select_related('utilisateur__user')
    demandes_acces = ferme.demandes_acces.filter(statut='en_attente').select_related('utilisateur__user') if is_proprietaire else []
    return render(request, 'fermes/detail_ferme.html', {
        'ferme': ferme,
        'projets': projets,
        'membres': membres,
        'demandes_acces': demandes_acces,
        'is_proprietaire': is_proprietaire,
        'can_manage_members': can_manage_members,
    })


@login_required
def modifier_ferme(request, ferme_id):
    ferme = get_object_or_404(Ferme, id=ferme_id, proprietaire=request.user.profile)
    if request.method == 'POST':
        form = FermeForm(request.POST, instance=ferme)
        if form.is_valid():
            form.save()
            messages.success(request, "Ferme modifiée avec succès.")
            return redirect('detail_ferme', ferme_id=ferme.id)
    else:
        form = FermeForm(instance=ferme)
    return render(request, 'fermes/modifier_ferme.html', {'form': form, 'ferme': ferme})


@login_required
def supprimer_ferme(request, ferme_id):
    ferme = get_object_or_404(Ferme, id=ferme_id, proprietaire=request.user.profile)
    if request.method == 'POST':
        ferme.delete()
        messages.success(request, "Ferme supprimée avec succès.")
        return redirect('liste_fermes')
    return render(request, 'fermes/supprimer_ferme.html', {'ferme': ferme})


@login_required
def ajouter_membre_ferme(request, ferme_id):
    ferme = get_object_or_404(Ferme, id=ferme_id)
    is_proprietaire = ferme.proprietaire == request.user.profile
    membership = ferme.membres.filter(utilisateur=request.user.profile).first()
    can_manage_members = is_proprietaire or (
        membership is not None and membership.peut_gerer_membres
    )
    if not can_manage_members:
        messages.error(request, "Vous n'avez pas le droit d'ajouter des membres à cette ferme.")
        return redirect('detail_ferme', ferme_id=ferme.id)

    if request.method == 'POST':
        form = MembreFermeForm(request.POST, ferme=ferme, can_delegate_members=is_proprietaire)
        if form.is_valid():
            profile = form.cleaned_data['username']
            membre, created = MembreFerme.objects.get_or_create(
                ferme=ferme,
                utilisateur=profile,
                defaults={
                    'role': form.cleaned_data['role'],
                    'peut_gerer_membres': form.cleaned_data.get('peut_gerer_membres', False),
                }
            )
            if not created:
                messages.info(request, f"{profile.user.username} est déjà membre de la ferme.")
                return redirect('detail_ferme', ferme_id=ferme.id)
            messages.success(request, f"{profile.user.username} ajouté à la ferme.")
            membre_email = profile.user.email
            if membre_email:
                _send_mail_safe(
                    subject=f"Vous avez été ajouté à la ferme {ferme.nom}",
                    message=(
                        f"Bonjour {profile.user.username},\n\n"
                        f"{request.user.get_full_name() or request.user.username} vous a ajouté comme {membre.get_role_display()} "
                        f"à la ferme {ferme.nom}.\n"
                        f"Connectez-vous à Andd Baay pour y accéder."
                    ),
                    recipient_list=[membre_email],
                )
            return redirect('detail_ferme', ferme_id=ferme.id)
    else:
        form = MembreFermeForm(ferme=ferme, can_delegate_members=is_proprietaire)
    return render(request, 'fermes/ajouter_membre.html', {
        'form': form,
        'ferme': ferme,
        'is_proprietaire': is_proprietaire,
        'can_manage_members': can_manage_members,
    })


@login_required
def retirer_membre_ferme(request, ferme_id, membre_id):
    ferme = get_object_or_404(Ferme, id=ferme_id, proprietaire=request.user.profile)
    membre = get_object_or_404(MembreFerme, id=membre_id, ferme=ferme)
    if request.method == 'POST':
        username = membre.utilisateur.user.username
        membre.delete()
        messages.success(request, f"{username} retiré de la ferme.")
        return redirect('detail_ferme', ferme_id=ferme.id)
    return render(request, 'fermes/retirer_membre.html', {'membre': membre, 'ferme': ferme})


def _send_mail_safe(subject, message, recipient_list):
    """Envoie un email en loggant les erreurs SMTP au lieu de les masquer silencieusement."""
    if not recipient_list:
        return
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
    except Exception as exc:
        logger.warning("Échec d'envoi d'email à %s: %s", recipient_list, exc)


@login_required
def demander_acces_ferme(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = DemandeAccesFermeForm(request.POST, user_profile=profile)
        if form.is_valid():
            window_start = timezone.now() - timedelta(hours=24)
            recent_count = DemandeAccesFerme.objects.filter(
                utilisateur=profile,
                date_demande__gte=window_start,
            ).count()
            if recent_count >= 5:
                messages.error(request, "Vous avez atteint la limite de demandes d'accès (5 par 24h). Réessayez plus tard.")
                return redirect('demander_acces_ferme')
            ferme = form.cleaned_data['code']
            demande = DemandeAccesFerme.objects.create(
                ferme=ferme,
                utilisateur=profile,
                code=ferme.code_acces,
            )
            proprietaire_email = ferme.proprietaire.user.email
            if proprietaire_email:
                _send_mail_safe(
                    subject=f"Demande d'accès à la ferme {ferme.nom}",
                    message=(
                        f"{request.user.get_full_name() or request.user.username} demande à rejoindre votre ferme {ferme.nom}.\n\n"
                        f"Code utilisé : {demande.code}\n"
                        f"Connectez-vous à Andd Baay pour approuver ou refuser cette demande."
                    ),
                    recipient_list=[proprietaire_email],
                )
            messages.success(request, "Votre demande a été envoyée au propriétaire de la ferme.")
            return redirect('liste_fermes')
    else:
        form = DemandeAccesFermeForm(user_profile=profile)
    return render(request, 'fermes/demander_acces.html', {'form': form})


@login_required
@require_POST
def traiter_demande_acces_ferme(request, ferme_id, demande_id, action):
    ferme = get_object_or_404(Ferme, id=ferme_id, proprietaire=request.user.profile)
    demande = get_object_or_404(DemandeAccesFerme, id=demande_id, ferme=ferme, statut='en_attente')
    demandeur_email = demande.utilisateur.user.email
    demandeur_username = demande.utilisateur.user.username
    if action == 'approuver':
        valid_roles = {'manager', 'technicien', 'ouvrier'}
        role = request.POST.get('role', 'ouvrier')
        if role not in valid_roles:
            role = 'ouvrier'
        peut_gerer_membres = bool(request.POST.get('peut_gerer_membres'))
        MembreFerme.objects.get_or_create(
            ferme=ferme,
            utilisateur=demande.utilisateur,
            defaults={'role': role, 'peut_gerer_membres': peut_gerer_membres}
        )
        demande.statut = 'approuvee'
        messages.success(request, f"{demandeur_username} a été ajouté à la ferme.")
        _send_mail_safe(
            subject=f"Votre demande d'accès à {ferme.nom} a été approuvée",
            message=(
                f"Bonjour {demandeur_username},\n\n"
                f"Votre demande d'accès à la ferme {ferme.nom} a été approuvée.\n"
                f"Vous pouvez désormais y accéder depuis Andd Baay."
            ),
            recipient_list=[demandeur_email] if demandeur_email else [],
        )
    elif action == 'refuser':
        demande.statut = 'refusee'
        messages.info(request, f"Demande de {demandeur_username} refusée.")
        _send_mail_safe(
            subject=f"Votre demande d'accès à {ferme.nom} a été refusée",
            message=(
                f"Bonjour {demandeur_username},\n\n"
                f"Votre demande d'accès à la ferme {ferme.nom} n'a pas été acceptée."
            ),
            recipient_list=[demandeur_email] if demandeur_email else [],
        )
    else:
        messages.error(request, "Action invalide.")
        return redirect('detail_ferme', ferme_id=ferme.id)
    demande.date_traitement = timezone.now()
    demande.save()
    return redirect('detail_ferme', ferme_id=ferme.id)


# ============================================================
# TÂCHES — gestion hiérarchique
# ============================================================

def _fermes_de_lutilisateur(profile):
    """Toutes les fermes où l'utilisateur est propriétaire ou membre."""
    return Ferme.objects.filter(
        Q(proprietaire=profile) | Q(membres__utilisateur=profile)
    ).distinct()


@login_required
def taches_liste(request):
    """Liste des tâches.
    - Propriétaire / Manager / Technicien : voient toutes les tâches des fermes
      où ils sont membres, plus celles qu'ils ont reçues.
    - Ouvrier : ne voit que les tâches qui lui sont assignées.
    Filtres GET : ?ferme=<id>&statut=<...>&assigne=mes|recues|toutes
    """
    profile = request.user.profile
    fermes_user = _fermes_de_lutilisateur(profile)

    # Détermine si l'utilisateur n'est qu'ouvrier (sans rôle supérieur ailleurs)
    roles_utilisateur = set()
    for ferme in fermes_user:
        roles_utilisateur.add(Tache.role_dans_ferme(profile, ferme))
    est_uniquement_ouvrier = roles_utilisateur and roles_utilisateur.issubset({'ouvrier'})

    if est_uniquement_ouvrier:
        taches = Tache.objects.filter(assigne_a=profile)
    else:
        taches = Tache.objects.filter(
            Q(ferme__in=fermes_user) & (
                Q(assigne_a=profile) | Q(assigne_par=profile) |
                Q(ferme__proprietaire=profile) |
                Q(ferme__membres__utilisateur=profile,
                  ferme__membres__role__in=['manager', 'technicien'])
            )
        ).distinct()

    # Filtres
    ferme_id = request.GET.get('ferme')
    if ferme_id:
        taches = taches.filter(ferme_id=ferme_id)
    statut = request.GET.get('statut')
    if statut:
        taches = taches.filter(statut=statut)
    assigne = request.GET.get('assigne')
    if assigne == 'mes':
        taches = taches.filter(assigne_a=profile)
    elif assigne == 'recues':
        taches = taches.filter(assigne_par=profile)

    taches = taches.select_related(
        'ferme', 'projet', 'assigne_a__user', 'assigne_par__user'
    ).order_by('statut', 'date_echeance', '-date_creation')

    # Compteurs par statut (sur le scope déjà filtré par ferme/role)
    base_qs = Tache.objects.filter(assigne_a=profile) if est_uniquement_ouvrier else \
        Tache.objects.filter(ferme__in=fermes_user).filter(
            Q(assigne_a=profile) | Q(assigne_par=profile) |
            Q(ferme__proprietaire=profile) |
            Q(ferme__membres__utilisateur=profile,
              ferme__membres__role__in=['manager', 'technicien'])
        ).distinct()
    if ferme_id:
        base_qs = base_qs.filter(ferme_id=ferme_id)
    compteurs = {
        'a_faire': base_qs.filter(statut='a_faire').count(),
        'en_cours': base_qs.filter(statut='en_cours').count(),
        'terminee': base_qs.filter(statut='terminee').count(),
        'annulee': base_qs.filter(statut='annulee').count(),
    }

    # Peut-il créer une tâche dans au moins une ferme ?
    peut_creer = any(
        Tache.roles_assignables_par(Tache.role_dans_ferme(profile, f))
        for f in fermes_user
    )

    return render(request, 'taches/liste.html', {
        'taches': taches,
        'fermes': fermes_user,
        'compteurs': compteurs,
        'filtre_ferme': ferme_id or '',
        'filtre_statut': statut or '',
        'filtre_assigne': assigne or '',
        'est_uniquement_ouvrier': est_uniquement_ouvrier,
        'peut_creer': peut_creer,
        'STATUT_CHOICES': Tache.STATUT_CHOICES,
    })


@login_required
def creer_tache(request, ferme_id=None):
    """Création d'une tâche dans une ferme. Le rôle de l'auteur conditionne
    les assignés possibles (cf. TacheForm)."""
    profile = request.user.profile
    fermes_user = _fermes_de_lutilisateur(profile)

    # Si la ferme n'est pas précisée, redirige vers une page de sélection
    # ou prend la première ferme où l'utilisateur peut créer des tâches.
    ferme = None
    if ferme_id:
        ferme = get_object_or_404(fermes_user, id=ferme_id)
    else:
        for f in fermes_user:
            if Tache.roles_assignables_par(Tache.role_dans_ferme(profile, f)):
                ferme = f
                break
        if ferme is None:
            messages.error(request, "Vous n'avez aucune ferme dans laquelle créer des tâches.")
            return redirect('taches_liste')

    role = Tache.role_dans_ferme(profile, ferme)
    if not Tache.roles_assignables_par(role):
        messages.error(request, "Votre rôle ne vous permet pas de créer des tâches dans cette ferme.")
        return redirect('taches_liste')

    if request.method == 'POST':
        form = TacheForm(request.POST, ferme=ferme, auteur=profile)
        if form.is_valid():
            tache = form.save(commit=False)
            tache.ferme = ferme
            tache.assigne_par = profile
            tache.save()
            messages.success(request, f"Tâche « {tache.titre} » créée et assignée à {tache.assigne_a.user.username}.")
            _notifier_creation_tache(tache, request.user)
            return redirect('tache_detail', tache_id=tache.id)
    else:
        form = TacheForm(ferme=ferme, auteur=profile)

    return render(request, 'taches/creer.html', {
        'form': form,
        'ferme': ferme,
        'fermes': fermes_user,
        'role': role,
    })


@login_required
def tache_detail(request, tache_id):
    profile = request.user.profile
    tache = get_object_or_404(
        Tache.objects.select_related('ferme', 'projet', 'assigne_a__user', 'assigne_par__user'),
        id=tache_id,
    )

    # Le membre doit avoir accès à la ferme de la tâche
    if not (tache.ferme.proprietaire_id == profile.id
            or tache.ferme.membres.filter(utilisateur=profile).exists()):
        messages.error(request, "Vous n'avez pas accès à cette tâche.")
        return redirect('taches_liste')

    peut_changer_statut = tache.peut_changer_statut(profile)
    peut_supprimer = tache.peut_etre_modifiee_par(profile)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'changer_statut' and peut_changer_statut:
            form = TacheStatutForm(request.POST)
            if form.is_valid():
                ancien_statut = tache.statut
                tache.statut = form.cleaned_data['statut']
                commentaire = form.cleaned_data.get('commentaire_retour', '').strip()
                if commentaire:
                    tache.commentaire_retour = commentaire
                if tache.statut == 'terminee' and ancien_statut != 'terminee':
                    tache.date_terminee = timezone.now()
                    _notifier_tache_terminee(tache, request.user)
                elif tache.statut != 'terminee':
                    tache.date_terminee = None
                tache.save()
                messages.success(request, f"Statut mis à jour : {tache.get_statut_display()}.")
                return redirect('tache_detail', tache_id=tache.id)
        elif action == 'supprimer' and peut_supprimer:
            titre = tache.titre
            tache.delete()
            messages.info(request, f"Tâche « {titre} » supprimée.")
            return redirect('taches_liste')
        else:
            messages.error(request, "Action non autorisée.")
            return redirect('tache_detail', tache_id=tache.id)

    statut_form = TacheStatutForm(initial={'statut': tache.statut})
    return render(request, 'taches/detail.html', {
        'tache': tache,
        'statut_form': statut_form,
        'peut_changer_statut': peut_changer_statut,
        'peut_supprimer': peut_supprimer,
    })


def _notifier_creation_tache(tache, auteur_user):
    email = tache.assigne_a.user.email
    if not email:
        return
    _send_mail_safe(
        subject=f"Nouvelle tâche : {tache.titre}",
        message=(
            f"Bonjour {tache.assigne_a.user.username},\n\n"
            f"{auteur_user.get_full_name() or auteur_user.username} vous a assigné une nouvelle tâche "
            f"dans la ferme {tache.ferme.nom}.\n\n"
            f"Titre      : {tache.titre}\n"
            f"Priorité   : {tache.get_priorite_display()}\n"
            f"Échéance   : {tache.date_echeance or 'aucune'}\n"
            f"Projet     : {tache.projet.nom if tache.projet else '—'}\n\n"
            f"{tache.description}\n\n"
            f"Connectez-vous à Andd Baay pour la consulter."
        ),
        recipient_list=[email],
    )


# ============================================================
# DASHBOARDS PAR RÔLE
# ============================================================

def _dashboard_manager(request, utilisateur, memberships):
    """Dashboard du manager : vue ferme(s) — projets, membres, tâches."""
    # Sélection ferme via ?ferme=<id>, sinon première ferme où il est manager
    fermes_managees = [m.ferme for m in memberships if m.role == 'manager']
    if not fermes_managees:
        fermes_managees = [m.ferme for m in memberships]

    selected_id = request.GET.get('ferme')
    selected = None
    if selected_id:
        selected = next((f for f in fermes_managees if str(f.id) == selected_id), None)
    if selected is None:
        selected = fermes_managees[0]

    projets = Projet.objects.filter(ferme=selected).select_related(
        'culture', 'localite'
    ).prefetch_related('projet_produits__produit').order_by('-date_lancement')

    projets_actifs = projets.filter(statut='en_cours').count()
    projets_finis = projets.filter(statut='fini').count()
    projets_pause = projets.filter(statut='en_pause').count()
    superficie_totale = projets.aggregate(s=Sum('superficie'))['s'] or 0
    superficie_active = projets.filter(statut='en_cours').aggregate(s=Sum('superficie'))['s'] or 0
    superficie_ferme = selected.superficie_totale or 0
    utilisation_pct = round((float(superficie_active) / float(superficie_ferme)) * 100, 1) if superficie_ferme else 0
    nombre_membres = selected.membres.count() + 1

    # Tâches de cette ferme
    taches = Tache.objects.filter(ferme=selected)
    taches_a_faire = taches.filter(statut='a_faire').count()
    taches_en_cours = taches.filter(statut='en_cours').count()
    taches_terminees = taches.filter(statut='terminee').count()
    taches_en_retard = sum(1 for t in taches.filter(statut__in=['a_faire', 'en_cours']) if t.est_en_retard)
    taches_recentes = taches.select_related('assigne_a__user', 'projet').order_by('-date_creation')[:8]

    return render(request, 'projets/dashboard_manager.html', {
        'utilisateur': utilisateur,
        'fermes': fermes_managees,
        'ferme': selected,
        'projets': projets[:10],
        'projets_total': projets.count(),
        'projets_actifs': projets_actifs,
        'projets_finis': projets_finis,
        'projets_pause': projets_pause,
        'superficie_totale': superficie_totale,
        'superficie_active': superficie_active,
        'superficie_ferme': superficie_ferme,
        'utilisation_pct': utilisation_pct,
        'nombre_membres': nombre_membres,
        'taches_a_faire': taches_a_faire,
        'taches_en_cours': taches_en_cours,
        'taches_terminees': taches_terminees,
        'taches_en_retard': taches_en_retard,
        'taches_recentes': taches_recentes,
    })


def _dashboard_technicien(request, utilisateur, memberships):
    """Dashboard technicien : focus sur l'évolution des cultures et produits."""
    fermes_user = [m.ferme for m in memberships]
    selected_id = request.GET.get('ferme')
    selected = None
    if selected_id:
        selected = next((f for f in fermes_user if str(f.id) == selected_id), None)
    if selected is None:
        selected = fermes_user[0]

    projets = Projet.objects.filter(ferme=selected).select_related(
        'culture', 'localite'
    ).prefetch_related('projet_produits__produit', 'prevision').order_by('-date_lancement')

    today = timezone.now().date()
    projets_data = []
    for p in projets:
        jours_ecoules = (today - p.date_lancement).days if p.date_lancement else 0
        cycle = getattr(p.culture, 'duree_cycle_jours', None) or 120
        progression = max(0, min(100, round((jours_ecoules / cycle) * 100))) if cycle else 0
        prevision = getattr(p, 'prevision', None)
        projets_data.append({
            'projet': p,
            'jours_ecoules': jours_ecoules,
            'progression': progression,
            'prevision': prevision,
        })

    nb_projets_actifs = projets.filter(statut='en_cours').count()
    cultures_distinctes = projets.values('culture__nom').distinct().count()

    # Prochaines récoltes (basé sur PrevisionRecolte si dispo, sinon date_lancement + cycle)
    recoltes_a_venir = []
    for d in projets_data[:15]:
        prev = d['prevision']
        if prev and prev.date_recolte_prevue and prev.date_recolte_prevue >= today:
            recoltes_a_venir.append({'projet': d['projet'], 'date': prev.date_recolte_prevue})
    recoltes_a_venir.sort(key=lambda r: r['date'])
    recoltes_a_venir = recoltes_a_venir[:6]

    # Tâches du technicien (créées + reçues) sur cette ferme
    mes_taches = Tache.objects.filter(
        ferme=selected
    ).filter(Q(assigne_a=utilisateur) | Q(assigne_par=utilisateur)).select_related(
        'assigne_a__user', 'assigne_par__user', 'projet'
    ).order_by('statut', '-date_creation')[:10]

    return render(request, 'projets/dashboard_technicien.html', {
        'utilisateur': utilisateur,
        'fermes': fermes_user,
        'ferme': selected,
        'projets_data': projets_data[:10],
        'nb_projets_actifs': nb_projets_actifs,
        'cultures_distinctes': cultures_distinctes,
        'recoltes_a_venir': recoltes_a_venir,
        'mes_taches': mes_taches,
    })


def _dashboard_ouvrier(request, utilisateur, memberships):
    """Dashboard ouvrier : uniquement ses tâches."""
    taches = Tache.objects.filter(assigne_a=utilisateur).select_related(
        'ferme', 'projet', 'assigne_par__user'
    ).order_by('statut', 'date_echeance', '-date_creation')

    a_faire = taches.filter(statut='a_faire')
    en_cours = taches.filter(statut='en_cours')
    terminees = taches.filter(statut='terminee')[:5]
    en_retard = sum(1 for t in taches.filter(statut__in=['a_faire', 'en_cours']) if t.est_en_retard)

    return render(request, 'projets/dashboard_ouvrier.html', {
        'utilisateur': utilisateur,
        'fermes': [m.ferme for m in memberships],
        'a_faire': a_faire,
        'en_cours': en_cours,
        'terminees': terminees,
        'a_faire_count': a_faire.count(),
        'en_cours_count': en_cours.count(),
        'terminees_count': taches.filter(statut='terminee').count(),
        'en_retard_count': en_retard,
    })


def _notifier_tache_terminee(tache, executant_user):
    if not tache.assigne_par:
        return
    email = tache.assigne_par.user.email
    if not email:
        return
    _send_mail_safe(
        subject=f"Tâche terminée : {tache.titre}",
        message=(
            f"Bonjour {tache.assigne_par.user.username},\n\n"
            f"{executant_user.get_full_name() or executant_user.username} a marqué la tâche "
            f"« {tache.titre} » (ferme {tache.ferme.nom}) comme terminée.\n\n"
            f"{('Commentaire : ' + tache.commentaire_retour) if tache.commentaire_retour else ''}"
        ),
        recipient_list=[email],
    )
