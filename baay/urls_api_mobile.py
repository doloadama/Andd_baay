# baay/urls_api_mobile.py
# ── Routes de l'API mobile v1 ─────────────────────────────────────────────
from django.urls import path

from .views_api_mobile import (
    FermeDetailView,
    FermeListCreateView,
    LocaliteListView,
    MeView,
    PrevisionRecolteListView,
    ProduitListView,
    ProjetDetailView,
    ProjetListCreateView,
    ProjetProduitDetailView,
    ProjetProduitListCreateView,
    RegionListView,
    RegisterView,
    TacheListCreateView,
    TacheUpdateView,
    commentaires_api,
    diagnostic_result_api,
    diagnostic_submit_api,
    mobile_dashboard_view,
    profile_api,
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

    # ── Tâches ────────────────────────────────────────────────────────────
    path("api/v1/taches/", TacheListCreateView.as_view(), name="api_v1_taches"),
    path("api/v1/taches/<uuid:pk>/statut/", TacheUpdateView.as_view(), name="api_v1_tache_statut"),

    # ── Commentaires ──────────────────────────────────────────────────────
    path("api/v1/commentaires/<str:ct_label>/<uuid:object_id>/", commentaires_api, name="api_v1_commentaires"),

    # ── Prévisions récolte ────────────────────────────────────────────────
    path("api/v1/previsions/", PrevisionRecolteListView.as_view(), name="api_v1_previsions"),

    # ── Profil utilisateur ────────────────────────────────────────────────
    path("api/v1/profile/", profile_api, name="api_v1_profile"),

    # ── Diagnostic async ──────────────────────────────────────────────────
    path("api/v1/diagnostic/", diagnostic_submit_api, name="api_v1_diagnostic_submit"),
    path("api/v1/diagnostic/<str:task_id>/", diagnostic_result_api, name="api_v1_diagnostic_result"),
]
