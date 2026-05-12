"""
Vues front-end pour la gestion des analyses de sol (HistoriqueSol).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from decimal import Decimal, InvalidOperation

from baay.models import Ferme, HistoriqueSol, ProduitAgricole
from baay.permissions import fermes_accessibles_qs


@login_required
def liste_analyses_sol(request):
    """Liste les analyses de sol des fermes de l'utilisateur."""
    profile = request.user.profile
    fermes = fermes_accessibles_qs(profile)
    analyses = HistoriqueSol.objects.filter(
        ferme__in=fermes
    ).select_related("ferme", "culture_precedente").order_by("-date_mesure")

    return render(request, "sols/liste_analyses.html", {
        "analyses": analyses,
    })


@login_required
def ajouter_analyse_sol(request):
    """Formulaire d'ajout d'une analyse de sol (front-end)."""
    profile = request.user.profile
    fermes = fermes_accessibles_qs(profile)
    produits = ProduitAgricole.objects.all().order_by("nom")

    # Pré-sélectionner la ferme si passée en GET
    ferme_preselected = request.GET.get("ferme")

    if request.method == "POST":
        form_data = request.POST

        # Récupération et validation
        ferme_id = form_data.get("ferme")
        parcelle_nom = form_data.get("parcelle_nom", "").strip()
        date_mesure = form_data.get("date_mesure")

        # Récupération des valeurs numériques
        def parse_decimal(value):
            if not value:
                return None
            try:
                return Decimal(str(value).replace(",", "."))
            except InvalidOperation:
                return None

        ph = parse_decimal(form_data.get("ph"))
        azote_ppm = parse_decimal(form_data.get("azote_ppm"))
        phosphore_ppm = parse_decimal(form_data.get("phosphore_ppm"))
        potassium_ppm = parse_decimal(form_data.get("potassium_ppm"))
        culture_precedente_id = form_data.get("culture_precedente") or None
        notes = form_data.get("notes", "").strip()

        # Validation
        errors = []
        if not ferme_id:
            errors.append("Veuillez sélectionner une ferme.")
        if not date_mesure:
            errors.append("La date du prélèvement est obligatoire.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, "sols/ajouter_analyse.html", {
                "fermes": fermes,
                "produits": produits,
                "form_data": form_data,
                "today": timezone.now().date().isoformat(),
            })

        # Récupération de la ferme
        try:
            ferme = fermes.get(id=ferme_id)
        except Ferme.DoesNotExist:
            messages.error(request, "Ferme introuvable.")
            return redirect("ajouter_analyse_sol")

        # Culture précédente
        culture_precedente = None
        if culture_precedente_id:
            try:
                culture_precedente = ProduitAgricole.objects.get(id=culture_precedente_id)
            except ProduitAgricole.DoesNotExist:
                pass

        # Création
        historique = HistoriqueSol.objects.create(
            ferme=ferme,
            parcelle_nom=parcelle_nom,
            date_mesure=date_mesure,
            ph=ph,
            azote_ppm=azote_ppm,
            phosphore_ppm=phosphore_ppm,
            potassium_ppm=potassium_ppm,
            culture_precedente=culture_precedente,
            notes=notes,
        )

        # Générer une recommandation automatique si possible
        try:
            recommandation = historique.analyser_et_recommander()
            if recommandation:
                messages.success(
                    request,
                    f"Analyse enregistrée ! {recommandation.get('message_explication', 'Recommandation générée.')}"
                )
            else:
                messages.success(request, "Analyse de sol enregistrée avec succès.")
        except Exception:
            messages.success(request, "Analyse de sol enregistrée avec succès.")

        return redirect("liste_analyses_sol")

    return render(request, "sols/ajouter_analyse.html", {
        "fermes": fermes,
        "produits": produits,
        "today": timezone.now().date().isoformat(),
        "ferme_preselected": ferme_preselected,
    })


@login_required
def detail_analyse_sol(request, analyse_id):
    """Détail d'une analyse avec recommandations."""
    profile = request.user.profile
    fermes = fermes_accessibles_qs(profile)

    analyse = get_object_or_404(
        HistoriqueSol.objects.select_related("ferme", "culture_precedente"),
        id=analyse_id,
        ferme__in=fermes,
    )

    # Recommandations liées
    recommandations = analyse.recommandations.select_related("culture_cible").order_by("-date_creation")

    return render(request, "sols/detail_analyse.html", {
        "analyse": analyse,
        "recommandations": recommandations,
    })
