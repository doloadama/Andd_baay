from django.urls import path

from baay.views_finance import (
    FinanceHubView,
    FinanceInvestissementCreateAjaxView,
    FinanceInvestissementDeleteView,
    FinanceInvestissementDuplicateView,
    FinanceProduitFilterPartialView,
    FinanceProduitSelectPartialView,
    FinanceRecetteCreateAjaxView,
    FinanceRecetteDeleteView,
    FinanceStatsPartialView,
)
from baay.views_finance_workflow import (
    liste_recettes_validation,
    partial_recette_validation,
    valider_recette,
    refuser_recette,
    partial_recette_row,
    compteur_recettes_attente,
    simulateur_roi,
    creer_simulation_roi,
    api_comparer_scenarios,
    supprimer_simulation,
)

urlpatterns = [
    path("finance/", FinanceHubView.as_view(), name="finance_hub"),
    path("finance/stats/", FinanceStatsPartialView.as_view(), name="finance_stats_partial"),
    path(
        "finance/produits-form/",
        FinanceProduitSelectPartialView.as_view(),
        name="finance_produits_form_partial",
    ),
    path(
        "finance/produits-filtre/",
        FinanceProduitFilterPartialView.as_view(),
        name="finance_produits_filter_partial",
    ),
    path(
        "finance/investissement/<uuid:pk>/dupliquer/",
        FinanceInvestissementDuplicateView.as_view(),
        name="finance_duplicate_investissement",
    ),
    path(
        "finance/investissement/<uuid:pk>/supprimer/",
        FinanceInvestissementDeleteView.as_view(),
        name="finance_delete_investissement",
    ),
    path(
        "finance/recette/<uuid:pk>/supprimer/",
        FinanceRecetteDeleteView.as_view(),
        name="finance_delete_recette",
    ),
    path(
        "finance/investissement/ajouter/",
        FinanceInvestissementCreateAjaxView.as_view(),
        name="finance_add_investissement",
    ),
    path(
        "finance/recette/ajouter/",
        FinanceRecetteCreateAjaxView.as_view(),
        name="finance_add_recette",
    ),
    # Workflow Validation Recettes (V2)
    path("finance/validation/", liste_recettes_validation, name="finance_validation_list"),
    path("finance/validation/compteur/", compteur_recettes_attente, name="finance_validation_compteur"),
    path("finance/recette/<str:recette_id>/validation-detail/", partial_recette_validation, name="recette_validation_detail"),
    path("finance/recette/<str:recette_id>/valider/", valider_recette, name="recette_valider"),
    path("finance/recette/<str:recette_id>/refuser/", refuser_recette, name="recette_refuser"),
    path("finance/recette/<str:recette_id>/row/", partial_recette_row, name="recette_row_refresh"),
    # Simulation ROI (V2)
    path("finance/projet/<str:projet_id>/simulateur-roi/", simulateur_roi, name="simulateur_roi"),
    path("finance/projet/<str:projet_id>/simulation-roi/creer/", creer_simulation_roi, name="creer_simulation_roi"),
    path("finance/projet/<str:projet_id>/scenarios-comparer/", api_comparer_scenarios, name="api_comparer_scenarios"),
    path("finance/simulation/<str:simulation_id>/supprimer/", supprimer_simulation, name="supprimer_simulation"),
]
