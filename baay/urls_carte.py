"""
URLs pour la carte de chaleur et marketplace géolocalisé.
"""

from django.urls import path
from baay.views_carte_geo import (
    carte_heatmap,
    api_geojson_heatmap,
    api_leaflet_heatmap_data,
    api_stats_heatmap,
    refresh_heatmap_cache,
    marketplace_liste,
    marketplace_detail_offre,
    marketplace_creer_offre_form,
    marketplace_creer_offre,
    marketplace_initier_transaction,
    marketplace_mes_offres,
    marketplace_mes_achats,
    marketplace_maj_statut_transaction,
)

app_name = "carte"

urlpatterns = [
    # Carte de chaleur
    path("carte/heatmap/", carte_heatmap, name="carte_heatmap"),
    path("api/carte/heatmap-geojson/", api_geojson_heatmap, name="api_geojson_heatmap"),
    path("api/carte/heatmap-data/", api_leaflet_heatmap_data, name="api_leaflet_heatmap"),
    path("api/carte/heatmap-stats/", api_stats_heatmap, name="api_stats_heatmap"),
    path("admin/carte/refresh-cache/", refresh_heatmap_cache, name="refresh_heatmap_cache"),

    # Marketplace
    path("marketplace/", marketplace_liste, name="marketplace_liste"),
    path("marketplace/offre/<str:offre_id>/", marketplace_detail_offre, name="marketplace_detail_offre"),
    path("marketplace/offre/creer/form/", marketplace_creer_offre_form, name="marketplace_creer_offre_form"),
    path("marketplace/offre/creer/", marketplace_creer_offre, name="marketplace_creer_offre"),
    path("marketplace/offre/<str:offre_id>/reserver/", marketplace_initier_transaction, name="marketplace_initier_transaction"),
    path("marketplace/mes-offres/", marketplace_mes_offres, name="marketplace_mes_offres"),
    path("marketplace/mes-achats/", marketplace_mes_achats, name="marketplace_mes_achats"),
    path("marketplace/transaction/<str:transaction_id>/statut/", marketplace_maj_statut_transaction, name="marketplace_maj_statut_transaction"),
]
