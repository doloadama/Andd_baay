"""
URLs pour le Dashboard Bento HTMX - Andd Baay V2
"""

from django.urls import path
from baay.views_bento import (
    bento_dashboard,
    set_ferme_active,
    bento_card_meteo,
    bento_card_projets,
    bento_projet_detail_card,
    bento_card_budget,
    bento_card_alertes_ia,
    bento_card_taches,
    bento_card_predictions,
    marquer_recommandation_vue,
    chatbot_agricole_query,
)
from baay.views_demo_data import (
    demo_dashboard_data,
    demo_finance_workflow,
    demo_marketplace,
    demo_roi_simulations,
    api_demo_data_summary,
)

app_name = "dashboard"

urlpatterns = [
    # Page principale Bento Dashboard
    path("dashboard/", bento_dashboard, name="bento_dashboard"),
    
    # Actions ferme
    path("dashboard/ferme/<str:ferme_id>/set-active/", set_ferme_active, name="set_ferme_active"),
    
    # Cartes Bento HTMX
    path("dashboard/bento/meteo/", bento_card_meteo, name="bento_card_meteo"),
    path("dashboard/bento/projets/", bento_card_projets, name="bento_card_projets"),
    path("dashboard/bento/projet/<str:projet_id>/detail/", bento_projet_detail_card, name="bento_projet_detail_card"),
    path("dashboard/bento/budget/", bento_card_budget, name="bento_card_budget"),
    path("dashboard/bento/budget/<str:projet_id>/", bento_card_budget, name="bento_card_budget_projet"),
    path("dashboard/bento/alertes/", bento_card_alertes_ia, name="bento_card_alertes_ia"),
    path("dashboard/bento/taches/", bento_card_taches, name="bento_card_taches"),
    path("dashboard/bento/predictions/", bento_card_predictions, name="bento_card_predictions"),
    
    # Actions sur recommandations
    path("dashboard/recommandation/<str:recommandation_id>/marquer-vue/", 
         marquer_recommandation_vue, name="marquer_recommandation_vue"),
    
    # API Chatbot
    path("api/chatbot/agricole/", chatbot_agricole_query, name="chatbot_agricole_query"),

    # Vues Démo pour visualisation données (développement/test)
    path("demo/", demo_dashboard_data, name="demo_dashboard"),
    path("demo/finance/", demo_finance_workflow, name="demo_finance"),
    path("demo/marketplace/", demo_marketplace, name="demo_marketplace"),
    path("demo/roi/", demo_roi_simulations, name="demo_roi"),
    path("api/demo/summary/", api_demo_data_summary, name="demo_api_summary"),
]
