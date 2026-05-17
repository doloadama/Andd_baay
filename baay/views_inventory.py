"""
Vues du module d'inventaire (intrants, récoltes, mouvements de stock).

Mobile-first, DaisyUI + HTMX pour les mises à jour en temps réel.
"""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from django.db.models import Q

from baay.models import Ferme, MouvementStock, ProduitAgricole, StockIntrant, StockRecolte
from baay.permissions import (
    peut_modifier_inventaire,
    peut_voir_inventaire,
    role_dans_ferme,
)
from baay.services.inventory_service import (
    ajuster_stock_intrant,
    stocks_en_alerte,
    volume_total_recoltes,
)


@login_required
def liste_inventaire(request, ferme_id):
    """Vue principale de l'inventaire d'une ferme (intrants, récoltes, mouvements)."""
    ferme = get_object_or_404(Ferme, id=ferme_id)
    profile = request.user.profile

    if not peut_voir_inventaire(profile, ferme):
        messages.error(request, "Vous n'avez pas accès à l'inventaire de cette ferme.")
        return redirect('detail_ferme', ferme_id=ferme.id)

    role = role_dans_ferme(profile, ferme)
    peut_modifier = peut_modifier_inventaire(profile, ferme)

    # Onglet actif (intrants par défaut)
    onglet = request.GET.get('onglet', 'intrants')
    if onglet not in ('intrants', 'recoltes', 'mouvements'):
        onglet = 'intrants'

    alertes = stocks_en_alerte(ferme)
    produits_disponibles = (
        ProduitAgricole.objects.filter(
            Q(projet_produits__projet__ferme=ferme) | Q(recoltes_stock__ferme=ferme)
        )
        .distinct()
        .order_by('nom')
    )

    context = {
        'ferme': ferme,
        'onglet': onglet,
        'role': role,
        'peut_modifier': peut_modifier,
        'alertes': alertes,
        'alertes_count': len(alertes),
        'volume_total': volume_total_recoltes(ferme),
        'intrants_count': StockIntrant.objects.filter(ferme=ferme).count(),
        'recoltes_count': StockRecolte.objects.filter(ferme=ferme).count(),
        'mouvements_count': MouvementStock.objects.filter(ferme=ferme).count(),
        'produits_disponibles': produits_disponibles,
    }

    if onglet == 'intrants':
        context['intrants'] = StockIntrant.objects.filter(ferme=ferme).order_by('-date_modification')
    elif onglet == 'recoltes':
        context['recoltes'] = StockRecolte.objects.filter(ferme=ferme).select_related('produit').order_by('-date_recolte')
    elif onglet == 'mouvements':
        context['mouvements'] = (
            MouvementStock.objects.filter(ferme=ferme)
            .select_related('stock_intrant', 'stock_recolte', 'stock_recolte__produit', 'utilisateur__user')
            .order_by('-date_mouvement')[:50]
        )

    return render(request, 'inventaire/liste_inventaire.html', context)


@login_required
def ajouter_intrant(request, ferme_id):
    """Créer un nouvel intrant dans l'inventaire."""
    ferme = get_object_or_404(Ferme, id=ferme_id)
    profile = request.user.profile

    if not peut_modifier_inventaire(profile, ferme):
        messages.error(request, "Vous n'avez pas le droit de modifier l'inventaire.")
        return redirect('liste_inventaire', ferme_id=ferme.id)

    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        categorie = request.POST.get('categorie', StockIntrant.CATEGORIE_AUTRE)
        quantite = Decimal(request.POST.get('quantite', '0'))
        unite = request.POST.get('unite', StockIntrant.UNITE_KG)
        seuil = Decimal(request.POST.get('seuil_alerte', '10'))

        if nom:
            StockIntrant.objects.create(
                ferme=ferme,
                nom=nom,
                categorie=categorie,
                quantite=quantite,
                unite=unite,
                seuil_alerte=seuil,
            )
            messages.success(request, f"'{nom}' ajouté à l'inventaire.")
        return redirect('liste_inventaire', ferme_id=ferme.id)

    return redirect('liste_inventaire', ferme_id=ferme.id)


@login_required
def modifier_intrant(request, ferme_id, intrant_id):
    """Modifier un intrant existant."""
    ferme = get_object_or_404(Ferme, id=ferme_id)
    intrant = get_object_or_404(StockIntrant, id=intrant_id, ferme=ferme)
    profile = request.user.profile

    if not peut_modifier_inventaire(profile, ferme):
        messages.error(request, "Vous n'avez pas le droit de modifier l'inventaire.")
        return redirect('liste_inventaire', ferme_id=ferme.id)

    if request.method == 'POST':
        intrant.nom = request.POST.get('nom', intrant.nom).strip()
        intrant.categorie = request.POST.get('categorie', intrant.categorie)
        intrant.quantite = Decimal(request.POST.get('quantite', intrant.quantite))
        intrant.unite = request.POST.get('unite', intrant.unite)
        intrant.seuil_alerte = Decimal(request.POST.get('seuil_alerte', intrant.seuil_alerte))
        intrant.save()
        messages.success(request, f"'{intrant.nom}' mis à jour.")

    return redirect('liste_inventaire', ferme_id=ferme.id)


@login_required
@require_POST
def ajuster_intrant_htmx(request, ferme_id, intrant_id):
    """Ajuste la quantité d'un intrant via HTMX (boutons +/-)."""
    ferme = get_object_or_404(Ferme, id=ferme_id)
    intrant = get_object_or_404(StockIntrant, id=intrant_id, ferme=ferme)
    profile = request.user.profile

    if not peut_modifier_inventaire(profile, ferme):
        return HttpResponse("<td colspan='5' class='text-error'>Permission refusée</td>")

    delta = Decimal(request.POST.get('delta', '0'))
    raison = request.POST.get('raison', 'Ajustement manuel')

    if delta != 0:
        ajuster_stock_intrant(
            stock_id=str(intrant.id),
            delta=delta,
            raison=raison,
            utilisateur=profile,
        )
        intrant.refresh_from_db()

    context = {
        'intrant': intrant,
        'alerte': intrant.quantite < intrant.seuil_alerte,
    }
    return render(request, 'inventaire/_intrant_row.html', context)


@login_required
def ajouter_recolte(request, ferme_id):
    """Ajouter une récolte au stock."""
    ferme = get_object_or_404(Ferme, id=ferme_id)
    profile = request.user.profile

    if not peut_modifier_inventaire(profile, ferme):
        messages.error(request, "Vous n'avez pas le droit de modifier l'inventaire.")
        return redirect('liste_inventaire', ferme_id=ferme.id)

    if request.method == 'POST':
        produit_id = request.POST.get('produit')
        quantite = Decimal(request.POST.get('quantite', '0'))
        unite = request.POST.get('unite', StockRecolte.UNITE_KG)
        date_recolte = request.POST.get('date_recolte')
        qualite = request.POST.get('qualite', StockRecolte.QUALITE_NC)

        from baay.models import ProduitAgricole
        produit = get_object_or_404(ProduitAgricole, id=produit_id)

        StockRecolte.objects.create(
            ferme=ferme,
            produit=produit,
            quantite=quantite,
            unite=unite,
            date_recolte=date_recolte,
            qualite=qualite,
        )
        messages.success(request, f"Récolte de '{produit.nom}' enregistrée.")

    return redirect('liste_inventaire', ferme_id=ferme.id)


@login_required
def supprimer_intrant(request, ferme_id, intrant_id):
    """Supprimer un intrant de l'inventaire."""
    ferme = get_object_or_404(Ferme, id=ferme_id)
    intrant = get_object_or_404(StockIntrant, id=intrant_id, ferme=ferme)
    profile = request.user.profile

    if not peut_modifier_inventaire(profile, ferme):
        messages.error(request, "Vous n'avez pas le droit de modifier l'inventaire.")
        return redirect('liste_inventaire', ferme_id=ferme.id)

    nom = intrant.nom
    intrant.delete()
    messages.success(request, f"'{nom}' supprimé de l'inventaire.")
    return redirect('liste_inventaire', ferme_id=ferme.id)
