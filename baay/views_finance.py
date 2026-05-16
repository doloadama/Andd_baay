"""Hub Finance : liste des dépenses, filtres et saisie."""

import json
import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views import View

from baay.forms import FinanceDepenseForm, FinanceRecetteForm
from baay.models import Depense, Investissement, Projet, ProjetProduit, ProduitAgricole, Recette
from baay.permissions import (
    peut_acceder_menu_finance,
    peut_modifier_investissement,
    projets_avec_vue_depenses_qs,
    projets_modifiables_depenses_qs,
)
from baay.services import (
    calculer_kpis_financiers_projet,
    check_budget_status,
    check_projet_produit_budget_status,
    investissement_montant_expr,
)

logger = logging.getLogger("baay")


def _deny_if_no_finance_access(request):
    if not request.user.is_authenticated or not peut_acceder_menu_finance(
        request.user.profile
    ):
        return HttpResponseForbidden(
            "Accès réservé aux gestionnaires (Propriétaire ou Manager)."
        )
    return None


def _apply_depense_filters(request, qs):
    projet_id = request.GET.get("projet")
    if projet_id:
        qs = qs.filter(projet_id=projet_id)
    scope = request.GET.get("produit_scope", "")
    if scope == "general":
        qs = qs.filter(projet_produit__isnull=True)
    elif scope and scope != "all":
        qs = qs.filter(projet_produit_id=scope)
    mois = request.GET.get("mois")
    annee = request.GET.get("annee")
    try:
        if annee:
            y = int(annee)
            qs = qs.filter(date_investissement__year=y)
        if mois:
            m = int(mois)
            qs = qs.filter(date_investissement__month=m)
    except (TypeError, ValueError):
        pass
    return qs


def _depense_queryset_for_user(request):
    profile = request.user.profile
    projets_visibles = projets_avec_vue_depenses_qs(profile)
    return (
        Investissement.objects.filter(projet__in=projets_visibles)
        .select_related(
            "projet",
            "projet__ferme",
            "projet_produit",
            "projet_produit__produit",
        )
        .order_by("-date_investissement", "-id")
    )


def _total_montant(qs):
    agg = qs.aggregate(
        t=Coalesce(Sum(investissement_montant_expr()), Value(Decimal("0"))),
    )
    return agg["t"] or Decimal("0")


def _redirect_finance_hub_preserving_query(request):
    q = request.GET.urlencode()
    base = reverse("finance_hub")
    if q:
        return redirect(f"{base}?{q}")
    return redirect(base)


def _projet_produits_options(projet_id):
    if not projet_id:
        return ProjetProduit.objects.none()
    return (
        ProjetProduit.objects.filter(projet_id=projet_id)
        .select_related("produit")
        .order_by("produit__nom")
    )


MONTH_OPTIONS_FR = [
    (1, "Janvier"),
    (2, "Février"),
    (3, "Mars"),
    (4, "Avril"),
    (5, "Mai"),
    (6, "Juin"),
    (7, "Juillet"),
    (8, "Août"),
    (9, "Septembre"),
    (10, "Octobre"),
    (11, "Novembre"),
    (12, "Décembre"),
]


def _finance_surface_reference(profile) -> dict:
    """
    Par projet modifiable : superficie projet + ha par ProjetProduit (comme hectaresPourLigne
    sur la fiche projet / ajouter investissement).
    """
    pps_qs = ProjetProduit.objects.only("id", "projet_id", "superficie_allouee")
    projets = projets_modifiables_depenses_qs(profile).prefetch_related(
        Prefetch("projet_produits", queryset=pps_qs)
    )
    out = {}
    for p in projets:
        ha = float(p.superficie or 0)
        pps = {}
        for pp in p.projet_produits.all():
            s = pp.superficie_allouee
            pps[str(pp.pk)] = float(s) if s is not None else None
        out[str(p.pk)] = {"ha": ha, "pps": pps}
    return out


def _finance_hub_extra_context(request):
    profile = request.user.profile
    pairs = list(projets_modifiables_depenses_qs(profile).values_list("pk", "superficie"))
    modify_ids = {pk for pk, _ in pairs}
    return {
        "finance_surface_reference": _finance_surface_reference(profile),
        "finance_modify_project_ids": modify_ids,
        "month_options": MONTH_OPTIONS_FR,
    }


def _recette_queryset_for_user(request):
    profile = request.user.profile
    projets_visibles = projets_avec_vue_depenses_qs(profile)
    return (
        Recette.objects.filter(projet__in=projets_visibles)
        .select_related(
            "projet",
            "projet__ferme",
            "projet_produit",
            "projet_produit__produit",
        )
        .order_by("-date_vente", "-date_creation")
    )


def _apply_recette_filters(request, qs):
    projet_id = request.GET.get("projet")
    if projet_id:
        qs = qs.filter(projet_id=projet_id)
    scope = request.GET.get("produit_scope", "")
    if scope == "general":
        qs = qs.filter(projet_produit__isnull=True)
    elif scope and scope != "all":
        qs = qs.filter(projet_produit_id=scope)
    mois = request.GET.get("mois")
    annee = request.GET.get("annee")
    try:
        if annee:
            qs = qs.filter(date_vente__year=int(annee))
        if mois:
            qs = qs.filter(date_vente__month=int(mois))
    except (TypeError, ValueError):
        pass
    return qs


def _total_recettes(qs):
    agg = qs.aggregate(t=Coalesce(Sum("montant_total"), Value(Decimal("0"))))
    return agg["t"] or Decimal("0")


def _querystring_without_pages(request):
    q = request.GET.copy()
    q.pop("page", None)
    q.pop("page_r", None)
    return q.urlencode()


def _finance_chart_year(request) -> int:
    annee = request.GET.get("annee")
    if annee:
        try:
            return int(annee)
        except (TypeError, ValueError):
            pass
    return now().year


def _build_finance_charts_data(request, depense_qs, recette_qs) -> dict:
    """Agrégats pour les graphiques (catégories + série mensuelle)."""
    year = _finance_chart_year(request)
    cat_labels = dict(Investissement.CATEGORIE_CHOICES)

    cat_rows = (
        depense_qs.values("categorie")
        .annotate(total=Coalesce(Sum(investissement_montant_expr()), Value(Decimal("0"))))
        .order_by("-total")
    )
    expenses_by_category = [
        {
            "label": cat_labels.get(row["categorie"], row["categorie"] or "Autre"),
            "amount": float(row["total"] or 0),
        }
        for row in cat_rows
        if row["total"] and row["total"] > 0
    ]

    monthly_recettes = []
    monthly_depenses = []
    for month in range(1, 13):
        monthly_depenses.append(
            float(
                _total_montant(
                    depense_qs.filter(
                        date_investissement__year=year,
                        date_investissement__month=month,
                    )
                )
            )
        )
        monthly_recettes.append(
            float(
                _total_recettes(
                    recette_qs.filter(date_vente__year=year, date_vente__month=month)
                )
            )
        )

    return {
        "chart_year": year,
        "chart_expenses": expenses_by_category,
        "chart_monthly": {
            "recettes": monthly_recettes,
            "depenses": monthly_depenses,
        },
    }


def _finance_hub_template_context(
    request,
    *,
    form_depense,
    form_recette,
    culture_partial_produits_depense=None,
    culture_partial_produits_recette=None,
):
    profile = request.user.profile
    projet_id = request.GET.get("projet")
    produits_qs = _projet_produits_options(projet_id)

    if culture_partial_produits_depense is None:
        culture_partial_produits_depense = produits_qs
    if culture_partial_produits_recette is None:
        culture_partial_produits_recette = produits_qs

    base_qs = _depense_queryset_for_user(request)
    qs = _apply_depense_filters(request, base_qs)
    paginator = Paginator(qs, 40)
    page_obj = paginator.get_page(request.GET.get("page"))

    base_r = _recette_queryset_for_user(request)
    qs_r = _apply_recette_filters(request, base_r)
    paginator_r = Paginator(qs_r, 40)
    page_obj_r = paginator_r.get_page(request.GET.get("page_r"))

    dep_pp = ""
    rec_pp = ""
    if request.method == "POST":
        dep_pp = request.POST.get("projet_produit", "")
        rec_pp = request.POST.get("recette-projet_produit", "")

    charts = _build_finance_charts_data(request, qs, qs_r)
    current_year = now().year
    years = list(range(current_year, current_year - 6, -1))

    return {
        "page_obj": page_obj,
        "depenses": page_obj,
        "page_obj_recettes": page_obj_r,
        "recettes": page_obj_r,
        "filter_projets": projets_avec_vue_depenses_qs(profile),
        "filter_projet_id": projet_id or "",
        "filter_mois": request.GET.get("mois") or "",
        "filter_annee": request.GET.get("annee") or "",
        "filter_produit_scope": request.GET.get("produit_scope") or "all",
        "produits_for_filter": produits_qs,
        "form_depense": form_depense,
        "form_recette": form_recette,
        "total_filtre": _total_montant(qs),
        "count_filtre": qs.count(),
        "total_recettes_filtre": _total_recettes(qs_r),
        "count_recettes_filtre": qs_r.count(),
        "filter_qs": _querystring_without_pages(request),
        "culture_partial_produits": culture_partial_produits_depense,
        "culture_partial_produits_recette": culture_partial_produits_recette,
        "selected_depense_projet_produit": dep_pp,
        "selected_recette_projet_produit": rec_pp,
        "total_depenses": _total_montant(qs),
        "total_recettes": _total_recettes(qs_r),
        "chart_year": charts["chart_year"],
        "chart_expenses": charts["chart_expenses"],
        "chart_monthly": charts["chart_monthly"],
        "years": years,
        "cultures": ProduitAgricole.objects.filter(
            projet__in=projets_avec_vue_depenses_qs(profile)
        )
        .distinct()
        .order_by("nom"),
        **_finance_hub_extra_context(request),
    }


def _build_kpis_data(request) -> dict:
    """
    Calcule les KPIs financiers agrégés pour initialiser le widget Alpine ROI.

    Important : on évite un N+1 (1 calcul/Projet). On agrège directement sur les projets visibles.
    Sémantique alignée sur `calculer_kpis_financiers_projet()` :
    - Total recettes = Somme `Recette.montant_total`
    - Total coûts    = Somme (lignes `Investissement` via `investissement_montant_expr()`) + Somme `Depense.montant`
    """
    profile = request.user.profile
    projets = projets_avec_vue_depenses_qs(profile)

    total_rec = (
        Recette.objects.filter(projet__in=projets)
        .aggregate(t=Coalesce(Sum("montant_total"), Value(Decimal("0"))))
        .get("t")
        or Decimal("0")
    )
    total_lignes_inv = (
        Investissement.objects.filter(projet__in=projets)
        .aggregate(t=Coalesce(Sum(investissement_montant_expr()), Value(Decimal("0"))))
        .get("t")
        or Decimal("0")
    )
    total_depenses_fiche = (
        Depense.objects.filter(projet__in=projets)
        .aggregate(t=Coalesce(Sum("montant"), Value(Decimal("0"))))
        .get("t")
        or Decimal("0")
    )

    return {
        "totalRecettes": float(total_rec),
        "totalCouts": float(total_lignes_inv + total_depenses_fiche),
        "typeOperation": "depense",
    }


@method_decorator(login_required, name="dispatch")
class FinanceHubView(View):
    template_name = "finance/finance_list.html"

    def dispatch(self, request, *args, **kwargs):
        resp = _deny_if_no_finance_access(request)
        if resp:
            return resp
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = _finance_hub_template_context(
            request,
            form_depense=FinanceDepenseForm(user=request.user),
            form_recette=FinanceRecetteForm(user=request.user),
            culture_partial_produits_depense=[],
            culture_partial_produits_recette=[],
        )
        context["kpis_data"] = _build_kpis_data(request)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        if request.POST.get("submit_recette"):
            form_recette = FinanceRecetteForm(request.POST, request.FILES, user=request.user)
            form_depense = FinanceDepenseForm(user=request.user)
            if not form_recette.is_valid():
                ctx = _finance_hub_template_context(
                    request,
                    form_depense=form_depense,
                    form_recette=form_recette,
                    culture_partial_produits_depense=[],
                    culture_partial_produits_recette=_projet_produits_options(
                        request.POST.get("recette-projet")
                    ),
                )
                ctx["kpis_data"] = _build_kpis_data(request)
                return render(request, self.template_name, ctx, status=400)

            projet = form_recette.cleaned_data["projet"]
            modifiables = projets_modifiables_depenses_qs(request.user.profile)
            if not modifiables.filter(pk=projet.pk).exists():
                messages.error(request, "Vous ne pouvez pas ajouter de recette pour ce projet.")
                return _redirect_finance_hub_preserving_query(request)
            if not peut_modifier_investissement(request.user.profile, projet):
                messages.error(request, "Vous ne pouvez pas ajouter de recette pour ce projet.")
                return _redirect_finance_hub_preserving_query(request)

            try:
                r = form_recette.save()
            except ValidationError as e:
                msg = e.messages[0] if getattr(e, "messages", None) else str(e)
                messages.error(request, msg)
                return _redirect_finance_hub_preserving_query(request)
            messages.success(
                request,
                f"Recette enregistrée — {r.montant_total.quantize(Decimal('1')):,.0f} FCFA (montant calculé).".replace(
                    ",", "\u202f"
                ),
            )
            return _redirect_finance_hub_preserving_query(request)

        # Défaut : dépense
        form_depense = FinanceDepenseForm(request.POST, request.FILES, user=request.user)
        form_recette = FinanceRecetteForm(user=request.user)
        if not form_depense.is_valid():
            ctx = _finance_hub_template_context(
                request,
                form_depense=form_depense,
                form_recette=form_recette,
                culture_partial_produits_depense=_projet_produits_options(
                    request.POST.get("projet")
                ),
                culture_partial_produits_recette=[],
            )
            ctx["kpis_data"] = _build_kpis_data(request)
            return render(request, self.template_name, ctx, status=400)

        projet = form_depense.cleaned_data["projet"]
        modifiables = projets_modifiables_depenses_qs(request.user.profile)
        if not modifiables.filter(pk=projet.pk).exists():
            messages.error(request, "Vous ne pouvez pas ajouter de dépense pour ce projet.")
            return _redirect_finance_hub_preserving_query(request)

        if not peut_modifier_investissement(request.user.profile, projet):
            messages.error(request, "Vous ne pouvez pas ajouter de dépense pour ce projet.")
            return _redirect_finance_hub_preserving_query(request)

        inv = form_depense.save(commit=False)
        inv.save()
        try:
            from baay.tasks import recompute_investment_budget_status_task

            recompute_investment_budget_status_task.delay(str(inv.projet_id))
        except Exception:
            logger.exception("Erreur déclenchement recompute budget (projet_id=%s)", inv.projet_id)

        over = False
        st = check_budget_status(inv.projet_id)
        if st.get("applicable") and st.get("over_budget"):
            over = True
        if inv.projet_produit_id:
            stp = check_projet_produit_budget_status(inv.projet_produit_id)
            if stp.get("applicable") and stp.get("over_budget"):
                over = True
        if not over:
            messages.success(request, "Dépense enregistrée.")

        return _redirect_finance_hub_preserving_query(request)


@method_decorator(login_required, name="dispatch")
class FinanceStatsPartialView(View):
    """Fragment HTMX : total et nombre de lignes filtrées."""

    def get(self, request, *args, **kwargs):
        resp = _deny_if_no_finance_access(request)
        if resp:
            return resp
        qs = _apply_depense_filters(request, _depense_queryset_for_user(request))
        qs_r = _apply_recette_filters(request, _recette_queryset_for_user(request))
        return render(
            request,
            "finance/_stats_bar.html",
            {
                "total_filtre": _total_montant(qs),
                "count_filtre": qs.count(),
                "total_recettes_filtre": _total_recettes(qs_r),
                "count_recettes_filtre": qs_r.count(),
            },
        )


@method_decorator(login_required, name="dispatch")
class FinanceProduitSelectPartialView(View):
    """Select « culture » pour les formulaires dépense / recette (hub Finance)."""

    def get(self, request, *args, **kwargs):
        resp = _deny_if_no_finance_access(request)
        if resp:
            return resp
        is_recette = request.GET.get("form") == "recette"
        projet_id = (
            request.GET.get("recette-projet")
            if is_recette
            else request.GET.get("projet")
        )
        field_name = "recette-projet_produit" if is_recette else "projet_produit"
        select_id = f"id_{field_name}"
        ctx_base = {"field_name": field_name, "select_id": select_id}
        if not projet_id:
            return render(
                request,
                "finance/_produit_select_form.html",
                {**ctx_base, "projet_produits": []},
            )
        projet = get_object_or_404(Projet, pk=projet_id)
        if not projets_modifiables_depenses_qs(request.user.profile).filter(
            pk=projet.pk
        ).exists():
            return HttpResponseForbidden()
        pps = _projet_produits_options(str(projet.pk))
        return render(
            request,
            "finance/_produit_select_form.html",
            {**ctx_base, "projet_produits": pps},
        )


@method_decorator(login_required, name="dispatch")
class FinanceProduitFilterPartialView(View):
    """Select options du filtre par culture."""

    def get(self, request, *args, **kwargs):
        resp = _deny_if_no_finance_access(request)
        if resp:
            return resp
        projet_id = request.GET.get("projet")
        if not projet_id:
            return render(
                request,
                "finance/_produit_filter_select.html",
                {
                    "projet_produits": [],
                    "produit_scope": request.GET.get("produit_scope") or "all",
                },
            )
        projet = get_object_or_404(Projet, pk=projet_id)
        if not projets_avec_vue_depenses_qs(request.user.profile).filter(pk=projet.pk).exists():
            return HttpResponseForbidden()
        pps = _projet_produits_options(str(projet.pk))
        return render(
            request,
            "finance/_produit_filter_select.html",
            {
                "projet_produits": pps,
                "produit_scope": request.GET.get("produit_scope") or "all",
            },
        )


@method_decorator(login_required, name="dispatch")
class FinanceInvestissementDuplicateView(View):
    """Duplique une ligne de dépense (même projet)."""

    def post(self, request, pk, *args, **kwargs):
        resp = _deny_if_no_finance_access(request)
        if resp:
            return resp
        inv = get_object_or_404(Investissement, pk=pk)
        if not _depense_queryset_for_user(request).filter(pk=inv.pk).exists():
            return HttpResponseForbidden()
        if not peut_modifier_investissement(request.user.profile, inv.projet):
            return HttpResponseForbidden()
        Investissement.objects.create(
            projet=inv.projet,
            projet_produit=inv.projet_produit,
            libelle=inv.libelle,
            categorie=inv.categorie,
            description=inv.description,
            cout_par_hectare=inv.cout_par_hectare,
            autres_frais=inv.autres_frais or Decimal("0"),
            date_investissement=inv.date_investissement,
        )
        messages.success(request, "Ligne dupliquée.")
        return _redirect_finance_hub_preserving_query(request)


@method_decorator(login_required, name="dispatch")
class FinanceInvestissementDeleteView(View):
    """Supprime une dépense."""

    def post(self, request, pk, *args, **kwargs):
        resp = _deny_if_no_finance_access(request)
        if resp:
            return resp
        inv = get_object_or_404(Investissement, pk=pk)
        if not _depense_queryset_for_user(request).filter(pk=inv.pk).exists():
            return HttpResponseForbidden()
        if not peut_modifier_investissement(request.user.profile, inv.projet):
            return HttpResponseForbidden()
        inv.delete()
        messages.success(request, "Dépense supprimée.")
        return _redirect_finance_hub_preserving_query(request)


@method_decorator(login_required, name="dispatch")
class FinanceRecetteDeleteView(View):
    """Supprime une recette (vente) enregistrée depuis le hub Finance."""

    def post(self, request, pk, *args, **kwargs):
        resp = _deny_if_no_finance_access(request)
        if resp:
            return resp
        rec = get_object_or_404(Recette, pk=pk)
        if not _recette_queryset_for_user(request).filter(pk=rec.pk).exists():
            return HttpResponseForbidden()
        if not peut_modifier_investissement(request.user.profile, rec.projet):
            return HttpResponseForbidden()
        try:
            rec.delete()
        except ValidationError as e:
            msg = e.messages[0] if getattr(e, "messages", None) else str(e)
            messages.error(request, msg)
            return _redirect_finance_hub_preserving_query(request)
        messages.success(request, "Recette supprimée.")
        return _redirect_finance_hub_preserving_query(request)


@method_decorator(login_required, name="dispatch")
class FinanceInvestissementCreateAjaxView(View):
    """Crée une nouvelle dépense (investissement) via AJAX depuis le hub Finance."""

    def post(self, request, *args, **kwargs):
        resp = _deny_if_no_finance_access(request)
        if resp:
            return JsonResponse({"success": False, "error": "Accès refusé"}, status=403)

        try:
            data = json.loads(request.body)
            projet_id = data.get("projet")
            projet_produit_id = data.get("projet_produit")
            libelle = data.get("libelle", "").strip()
            categorie = data.get("categorie", Investissement.CATEGORIE_GENERAL)
            cout_par_hectare = Decimal(str(data.get("cout_par_hectare", 0)))
            autres_frais = Decimal(str(data.get("autres_frais", 0)))
            date_investissement = data.get("date_investissement")

            projet = get_object_or_404(Projet, pk=projet_id)
            if not peut_modifier_investissement(request.user.profile, projet):
                return JsonResponse({"success": False, "error": "Permission refusée"}, status=403)

            inv = Investissement.objects.create(
                projet=projet,
                projet_produit_id=projet_produit_id or None,
                libelle=libelle,
                categorie=categorie,
                cout_par_hectare=cout_par_hectare,
                autres_frais=autres_frais,
                date_investissement=date_investissement or now(),
            )

            return JsonResponse({
                "success": True,
                "id": str(inv.id),
                "libelle": inv.libelle_affichage(),
                "montant": str(inv.calculer_investissement_total()),
                "date": inv.date_investissement.strftime("%d/%m/%Y"),
                "message": "Dépense ajoutée avec succès"
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)


@method_decorator(login_required, name="dispatch")
class FinanceRecetteCreateAjaxView(View):
    """Crée une nouvelle recette (vente) via AJAX depuis le hub Finance."""

    def post(self, request, *args, **kwargs):
        resp = _deny_if_no_finance_access(request)
        if resp:
            return JsonResponse({"success": False, "error": "Accès refusé"}, status=403)

        try:
            data = json.loads(request.body)
            projet_id = data.get("projet")
            projet_produit_id = data.get("projet_produit")
            produit = data.get("produit", "").strip()
            quantite = Decimal(str(data.get("quantite", 0)))
            unite = data.get("unite", Recette.UNITE_KG)
            prix_unitaire = Decimal(str(data.get("prix_unitaire", 0)))
            date_vente = data.get("date_vente")

            projet = get_object_or_404(Projet, pk=projet_id)
            if not peut_modifier_investissement(request.user.profile, projet):
                return JsonResponse({"success": False, "error": "Permission refusée"}, status=403)

            rec = Recette.objects.create(
                projet=projet,
                projet_produit_id=projet_produit_id or None,
                produit=produit,
                quantite=quantite,
                unite=unite,
                prix_unitaire=prix_unitaire,
                date_vente=date_vente or now(),
            )

            return JsonResponse({
                "success": True,
                "id": str(rec.id),
                "produit": rec.produit or (rec.projet_produit.produit.nom if rec.projet_produit else "Produit"),
                "montant": str(rec.montant_total),
                "date": rec.date_vente.strftime("%d/%m/%Y"),
                "message": "Recette ajoutée avec succès"
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
