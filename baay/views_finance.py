"""Hub Finance : liste des dépenses, filtres et saisie."""

import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from baay.forms import FinanceDepenseForm
from baay.models import Investissement, Projet, ProjetProduit
from baay.permissions import (
    peut_acceder_menu_finance,
    peut_modifier_investissement,
    projets_avec_vue_depenses_qs,
    projets_modifiables_depenses_qs,
)
from baay.services import (
    check_budget_status,
    check_projet_produit_budget_status,
    investissement_montant_expr,
)


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


def _querystring_without_page(request):
    q = request.GET.copy()
    q.pop("page", None)
    return q.urlencode()


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


def _finance_hub_extra_context(request):
    profile = request.user.profile
    pairs = list(projets_modifiables_depenses_qs(profile).values_list("pk", "superficie"))
    surfaces = {str(pk): float(sup or 0) for pk, sup in pairs}
    modify_ids = {pk for pk, _ in pairs}
    return {
        "projet_superficies_json": json.dumps(surfaces),
        "finance_modify_project_ids": modify_ids,
        "month_options": MONTH_OPTIONS_FR,
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
        base_qs = _depense_queryset_for_user(request)
        qs = _apply_depense_filters(request, base_qs)
        paginator = Paginator(qs, 40)
        page_obj = paginator.get_page(request.GET.get("page"))
        projets_filtre = projets_avec_vue_depenses_qs(request.user.profile)
        form_depense = FinanceDepenseForm(user=request.user)

        projet_id = request.GET.get("projet")
        produits_qs = _projet_produits_options(projet_id)

        context = {
            "page_obj": page_obj,
            "depenses": page_obj,
            "filter_projets": projets_filtre,
            "filter_projet_id": projet_id or "",
            "filter_mois": request.GET.get("mois") or "",
            "filter_annee": request.GET.get("annee") or "",
            "filter_produit_scope": request.GET.get("produit_scope") or "all",
            "produits_for_filter": produits_qs,
            "form_depense": form_depense,
            "total_filtre": _total_montant(qs),
            "count_filtre": qs.count(),
            "filter_qs": _querystring_without_page(request),
            "culture_partial_produits": [],
            **_finance_hub_extra_context(request),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form_depense = FinanceDepenseForm(request.POST, user=request.user)
        base_qs = _depense_queryset_for_user(request)
        qs = _apply_depense_filters(request, base_qs)
        paginator = Paginator(qs, 40)
        page_obj = paginator.get_page(request.GET.get("page"))
        projet_id = request.GET.get("projet")
        produits_qs = _projet_produits_options(projet_id)

        def _error_render():
            return render(
                request,
                self.template_name,
                {
                    "page_obj": page_obj,
                    "depenses": page_obj,
                    "filter_projets": projets_avec_vue_depenses_qs(request.user.profile),
                    "filter_projet_id": projet_id or "",
                    "filter_mois": request.GET.get("mois") or "",
                    "filter_annee": request.GET.get("annee") or "",
                    "filter_produit_scope": request.GET.get("produit_scope") or "all",
                    "produits_for_filter": produits_qs,
                    "form_depense": form_depense,
                    "total_filtre": _total_montant(qs),
                    "count_filtre": qs.count(),
                    "filter_qs": _querystring_without_page(request),
                    "culture_partial_produits": _projet_produits_options(request.POST.get("projet")),
                    **_finance_hub_extra_context(request),
                },
                status=400,
            )

        if not form_depense.is_valid():
            return _error_render()

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
        return render(
            request,
            "finance/_stats_bar.html",
            {
                "total_filtre": _total_montant(qs),
                "count_filtre": qs.count(),
            },
        )


@method_decorator(login_required, name="dispatch")
class FinanceProduitSelectPartialView(View):
    """Select « culture » pour le formulaire de nouvelle dépense."""

    def get(self, request, *args, **kwargs):
        resp = _deny_if_no_finance_access(request)
        if resp:
            return resp
        projet_id = request.GET.get("projet")
        if not projet_id:
            return render(
                request,
                "finance/_produit_select_form.html",
                {"projet_produits": [], "field_name": "projet_produit"},
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
            {"projet_produits": pps, "field_name": "projet_produit"},
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
