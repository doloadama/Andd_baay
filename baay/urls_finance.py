from django.urls import path

from baay.views_finance import (
    FinanceHubView,
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
]
