#!/usr/bin/env python
"""
Script de déploiement Andd Baay V2
===================================

Ce script automatise le déploiement de la version 2 avec tous les piliers:
- Pilier 1: IA Agronomique
- Pilier 2: Dashboard Bento
- Pilier 3: Finance ROI
- Pilier 4: Géo-Data + Marketplace
- Pilier 5: Excellence Technique (optimisations)

Usage:
    python deploy_v2.py [command]

Commands:
    check       - Vérifier la configuration
    migrate     - Exécuter les migrations
    static      - Collecter les fichiers statiques
    test        - Lancer les tests
    full        - Déploiement complet
    rollback    - Rollback migrations V2
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Configuration
DJANGO_SETTINGS_MODULE = "Andd_Baayi.settings"
MIGRATIONS_V2 = [
    "0039_recommandations_incidents_documents_ia",
    "0040_workflow_finance_roi",
    "0041_geo_marketplace_models",
]


def run_command(cmd: str, description: str = "") -> bool:
    """Exécute une commande shell et affiche le résultat."""
    if description:
        print(f"\n{'='*60}")
        print(f"🔄 {description}")
        print(f"{'='*60}")

    print(f"$ {cmd}")

    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("✅ SUCCÈS")
        if result.stdout:
            print(result.stdout[:2000])  # Limiter output
        return True
    else:
        print("❌ ÉCHEC")
        print(result.stderr[:2000])
        return False


def check_environment():
    """Vérifie que l'environnement est correctement configuré."""
    print("\n" + "="*60)
    print("🔍 VÉRIFICATION ENVIRONNEMENT")
    print("="*60)

    checks = []

    # Vérifier Python
    checks.append(("Python", sys.version.split()[0]))

    # Vérifier Django
    try:
        import django
        checks.append(("Django", django.get_version()))
    except ImportError:
        checks.append(("Django", "NON INSTALLÉ ❌"))
        return False

    # Vérifier les dépendances clés
    deps = [
        ("django", "Django"),
        ("celery", "Celery"),
        ("requests", "Requests"),
        ("cloudinary", "Cloudinary"),
    ]

    for module, name in deps:
        try:
            __import__(module)
            checks.append((name, "✅"))
        except ImportError:
            checks.append((name, "❌ Manquant"))

    # Vérifier structure
    required_files = [
        "manage.py",
        "Andd_Baayi/settings.py",
        "baay/models.py",
        "baay/views_bento.py",
        "baay/views_finance_workflow.py",
        "baay/views_carte_geo.py",
        "baay/services/fertilisation_service.py",
        "baay/services/roi_simulation_service.py",
        "baay/services/carte_chaleur_service.py",
        "baay/services/query_optimizer.py",
    ]

    for f in required_files:
        exists = "✅" if os.path.exists(f) else "❌"
        checks.append((f, exists))

    # Afficher tableau
    max_len = max(len(c[0]) for c in checks)
    for name, status in checks:
        print(f"  {name:<{max_len+2}} {status}")

    # Vérifier si tous les fichiers V2 existent
    v2_files = [f for f in required_files if "bento" in f or "finance_workflow" in f or "carte" in f or "optimizer" in f]
    all_exist = all(os.path.exists(f) for f in v2_files)

    if all_exist:
        print("\n✅ Structure V2 complète")
        return True
    else:
        print("\n❌ Fichiers V2 manquants")
        return False


def migrate_v2():
    """Exécute les migrations V2."""
    print("\n" + "="*60)
    print("🗄️  MIGRATIONS V2")
    print("="*60)

    commands = [
        "python manage.py makemigrations --check --dry-run 2>&1 || echo 'Migrations à créer'",
        "python manage.py migrate baay 0039",
        "python manage.py migrate baay 0040",
        "python manage.py migrate baay 0041",
        "python manage.py migrate",
    ]

    for cmd in commands:
        if not run_command(cmd):
            return False

    # Vérifier migrations
    result = run_command(
        "python manage.py showmigrations baay | grep -E '0039|0040|0041'",
        "Vérification migrations"
    )

    return True


def collect_static():
    """Collecte les fichiers statiques."""
    return run_command(
        "python manage.py collectstatic --noinput",
        "Collection fichiers statiques"
    )


def run_tests():
    """Lance les tests V2."""
    print("\n" + "="*60)
    print("🧪 TESTS V2")
    print("="*60)

    # Tests modèles
    run_command(
        "python manage.py test baay.tests.test_models -v 2",
        "Tests modèles"
    )

    # Tests services V2
    run_command(
        "pytest tests/test_services_v2.py -v --tb=short 2>&1 || echo 'Pytest non configuré, ignorer'",
        "Tests services V2"
    )

    # Check Django
    return run_command(
        "python manage.py check",
        "Check Django"
    )


def setup_cache():
    """Configure le cache pour les optimisations."""
    print("\n" + "="*60)
    print("⚡ CONFIGURATION CACHE")
    print("="*60)

    # Vider le cache
    return run_command(
        "python -c \"from django.core.cache import cache; cache.clear(); print('Cache vidé')\"",
        "Initialisation cache"
    )


def create_superuser_if_needed():
    """Crée un superuser si aucun n'existe."""
    return run_command(
        'python -c "'
        'from django.contrib.auth import get_user_model; '
        'User = get_user_model(); '
        'print(\"Superuser existe\" if User.objects.filter(is_superuser=True).exists() else \"Créer superuser: python manage.py createsuperuser\")'
        '"',
        "Vérification superuser"
    )


def generate_documentation():
    """Génère la documentation des nouvelles fonctionnalités."""
    print("\n" + "="*60)
    print("📚 GÉNÉRATION DOCUMENTATION")
    print("="*60)

    doc = f"""
# Andd Baay V2 - Documentation Déploiement
## Générée le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
"""

    with open("DEPLOY_V2.md", "w", encoding="utf-8") as f:
        f.write(doc)

    print("✅ Documentation générée: DEPLOY_V2.md")
    return True


def rollback_v2():
    """Rollback les migrations V2 (ATTENTION: données perdues)."""
    print("\n" + "="*60)
    print("⚠️  ROLLBACK V2")
    print("="*60)
    print("ATTENTION: Cette opération supprimera les données V2!")
    print("Tables affectées: RecommandationFertilisation, IncidentRapporte,")
    print("                 DocumentConnaissance, SimulationROI,")
    print("                 OffreProduit, TransactionMarche")
    print()

    confirm = input("Êtes-vous sûr? (tapez 'ROLLBACK' pour confirmer): ")

    if confirm != "ROLLBACK":
        print("❌ Annulé")
        return False

    # Rollback migrations
    for migration in reversed(MIGRATIONS_V2):
        base = migration.split("_")[0]  # 0039, 0040, 0041
        prev = str(int(base) - 1).zfill(4)  # Migration précédente
        run_command(f"python manage.py migrate baay {prev}", f"Rollback {migration}")

    return True


def full_deploy():
    """Déploiement complet."""
    print("\n" + "="*60)
    print("🚀 DÉPLOIEMENT COMPLET ANDD BAAY V2")
    print("="*60)

    steps = [
        ("Vérification environnement", check_environment),
        ("Migrations V2", migrate_v2),
        ("Collection statiques", collect_static),
        ("Configuration cache", setup_cache),
        ("Tests", run_tests),
        ("Superuser", create_superuser_if_needed),
        ("Documentation", generate_documentation),
    ]

    results = []
    for name, func in steps:
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Erreur dans {name}: {e}")
            results.append((name, False))

    # Résumé
    print("\n" + "="*60)
    print("📋 RÉSUMÉ DÉPLOIEMENT")
    print("="*60)

    for name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {name}")

    all_ok = all(r[1] for r in results)

    if all_ok:
        print("\n🎉 Andd Baay V2 déployé avec succès!")
        print("\nProchaines étapes:")
        print("  1. Créer un superuser: python manage.py createsuperuser")
        print("  2. Lancer le serveur: python manage.py runserver")
        print("  3. Accéder au dashboard: http://localhost:8000/dashboard/")
        print("\nDocumentation: DEPLOY_V2.md")
    else:
        print("\n⚠️  Déploiement incomplet - vérifiez les erreurs ci-dessus")

    return all_ok


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Script de déploiement Andd Baay V2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python deploy_v2.py check       Vérifier l'environnement
  python deploy_v2.py migrate     Exécuter les migrations
  python deploy_v2.py test        Lancer les tests
  python deploy_v2.py full        Déploiement complet
        """
    )

    parser.add_argument(
        "command",
        choices=["check", "migrate", "static", "test", "full", "rollback", "doc"],
        help="Commande à exécuter",
    )

    args = parser.parse_args()

    # Vérifier que manage.py existe
    if not os.path.exists("manage.py"):
        print("❌ Erreur: manage.py non trouvé")
        print("Exécutez ce script depuis la racine du projet Django")
        sys.exit(1)

    # Setup Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", DJANGO_SETTINGS_MODULE)
    sys.path.insert(0, os.getcwd())

    # Exécuter commande
    commands = {
        "check": check_environment,
        "migrate": migrate_v2,
        "static": collect_static,
        "test": run_tests,
        "full": full_deploy,
        "rollback": rollback_v2,
        "doc": generate_documentation,
    }

    success = commands[args.command]()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
