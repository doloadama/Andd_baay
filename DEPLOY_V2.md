
# Andd Baay V2 - Documentation Déploiement
## Générée le: 2026-05-11 16:51:28

## 🎯 Piliers Implémentés

### Pilier 1: IA Agronomique
- **Modèles**: RecommandationFertilisation, IncidentRapporte, DocumentConnaissance
- **Services**: fertilisation_service.py, voice_assistant_service.py, rag_service.py
- **URLs**: /api/chatbot/agricole/

### Pilier 2: Dashboard Bento
- **Vues**: views_bento.py
- **Templates**: templates/dashboard/bento_*.html
- **URLs**: /dashboard/

### Pilier 3: Finance ROI
- **Modèles**: SimulationROI + workflow Recette
- **Services**: roi_simulation_service.py
- **Vues**: views_finance_workflow.py
- **URLs**: /finance/validation/, /finance/projet/<id>/simulateur-roi/

### Pilier 4: Géo-Data & Marketplace
- **Modèles**: OffreProduit, TransactionMarche
- **Services**: carte_chaleur_service.py
- **Vues**: views_carte_geo.py
- **URLs**: /carte/heatmap/, /marketplace/

### Pilier 5: Excellence Technique
- **Optimisations**: query_optimizer.py
- **Cache**: Redis/Memory cache pour heatmap et stats

## 🚀 URLs Principales

| URL | Description |
|-----|-------------|
| /dashboard/ | Dashboard Bento V2 |
| /finance/validation/ | Workflow validation recettes |
| /finance/projet/<id>/simulateur-roi/ | Simulateur ROI |
| /carte/heatmap/ | Carte des cultures |
| /marketplace/ | Marketplace interne |
| /api/chatbot/agricole/ | API Chatbot agricole |

## 🧪 Tests

```bash
# Tests unitaires
pytest tests/test_services_v2.py -v

# Tests Django
python manage.py test baay.tests

# Check complet
python manage.py check
```

## 📊 Migrations V2

- `0039_recommandations_incidents_documents_ia` - IA Agronomique
- `0040_workflow_finance_roi` - Finance workflow + SimulationROI
- `0041_geo_marketplace_models` - Marketplace models

## 🔧 Commandes Utiles

```bash
# Déploiement complet
python deploy_v2.py full

# Vérification
python deploy_v2.py check

# Tests
python deploy_v2.py test

# Rollback V2 (attention!)
python deploy_v2.py rollback
```

## 📦 Dépendances

Assurez-vous d'avoir:
- Django >= 4.2
- Celery (pour tâches async)
- Redis (pour cache)
- Leaflet.js (CDN pour carte)
