from django.urls import path

from baay.views_finance import (
    FinanceHubView,
    FinanceInvestissementDeleteView,
    FinanceInvestissementDuplicateView,
    FinanceProduitFilterPartialView,
    FinanceProduitSelectPartialView,
    FinanceStatsPartialView,
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
]
