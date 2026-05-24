# baay/urls_api_mobile.py
# ── Routes de l'API mobile v1 ─────────────────────────────────────────────
from django.urls import path

from .views_api_mobile import (
    FermeDetailView,
    FermeListCreateView,
    LocaliteListView,
    MeView,
    ProduitListView,
    ProjetDetailView,
    ProjetListCreateView,
    ProjetProduitDetailView,
    ProjetProduitListCreateView,
    RegionListView,
    RegisterView,
    mobile_dashboard_view,
    projet_avancement_view,
    projet_produit_etat_view,
    projet_statut_view,
)

_p = "api/mobile"

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────
    path(f"{_p}/auth/register/", RegisterView.as_view(), name="mobile_register"),
    path(f"{_p}/auth/me/", MeView.as_view(), name="mobile_me"),

    # ── Dashboard ─────────────────────────────────────────────────────────
    path(f"{_p}/dashboard/", mobile_dashboard_view, name="mobile_dashboard"),

    # ── Géographie ────────────────────────────────────────────────────────
    path(f"{_p}/regions/", RegionListView.as_view(), name="mobile_regions"),
    path(f"{_p}/localites/", LocaliteListView.as_view(), name="mobile_localites"),

    # ── Catalogue produits ────────────────────────────────────────────────
    path(f"{_p}/produits/", ProduitListView.as_view(), name="mobile_produits"),

    # ── Fermes ────────────────────────────────────────────────────────────
    path(f"{_p}/fermes/", FermeListCreateView.as_view(), name="mobile_fermes"),
    path(f"{_p}/fermes/<uuid:ferme_id>/", FermeDetailView.as_view(), name="mobile_ferme_detail"),

    # ── Projets (imbriqués sous ferme) ────────────────────────────────────
    path(f"{_p}/fermes/<uuid:ferme_id>/projets/", ProjetListCreateView.as_view(), name="mobile_projets"),

    # ── Projets (accès direct par uuid) ───────────────────────────────────
    path(f"{_p}/projets/<uuid:projet_id>/", ProjetDetailView.as_view(), name="mobile_projet_detail"),
    path(f"{_p}/projets/<uuid:projet_id>/statut/", projet_statut_view, name="mobile_projet_statut"),
    path(f"{_p}/projets/<uuid:projet_id>/avancement/", projet_avancement_view, name="mobile_projet_avancement"),

    # ── Produits du projet ────────────────────────────────────────────────
    path(f"{_p}/projets/<uuid:projet_id>/produits/", ProjetProduitListCreateView.as_view(), name="mobile_pp_list"),
    path(f"{_p}/projet-produits/<uuid:pp_id>/", ProjetProduitDetailView.as_view(), name="mobile_pp_detail"),
    path(f"{_p}/projet-produits/<uuid:pp_id>/etat/", projet_produit_etat_view, name="mobile_pp_etat"),
]
