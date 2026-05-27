# Andd Baay Plans.md

Créé: 2026-05-27

---

## Phase 1: README — Amélioration du flux d'onboarding

| Task | Contenu | DoD | Depends | Status |
|------|---------|-----|---------|--------|
| 1.1 | **Réorganiser la structure** — Déplacer "Démarrage rapide" en tête (avant Stack et Architecture). Stack et Architecture passent en section secondaire. | La section "Démarrage rapide" apparaît avant la ligne 20 du README. | — | cc:完了 |
| 1.2 | **Compléter les prérequis** — Mentionner `.python-version` (Python 3.12 fixé par le fichier), ajouter `pip install -r requirements-dev.txt` pour les contributeurs, clarifier Windows vs Linux/Mac activate. | Section Prérequis liste `.python-version`, `requirements-dev.txt`, et les deux commandes activate. | 1.1 | cc:完了 |
| 1.3 | **Ajouter une étape "Vérifier l'installation"** — Après `runserver`, ajouter un bloc de vérification : URL à ouvrir (`http://localhost:8000`), page attendue (formulaire login), et commande de smoke test (`python manage.py check`). | README contient un bloc "Vérifier" avec URL, page attendue, et commande check. | 1.1 | cc:完了 |
| 1.4 | **Ajouter un utilisateur de démo** — Documenter la commande `createsuperuser` avec un exemple de credentials de démo (`admin@example.com / changeme123`) pour que le premier login soit immédiat. | README contient exemple de commande createsuperuser avec credentials exemple clairs. | 1.2 | cc:完了 |
| 1.5 | **Corriger le placeholder clone URL** — Remplacer `<url-du-depot>` par une URL GitHub structurée (`https://github.com/<votre-compte>/andd-baay.git`). | Aucune occurrence de `<url-du-depot>` dans le README. | — | cc:完了 |
| 1.6 | **Unifier la section Tests** — Mentionner `pytest` (fichier `pytest.ini` présent) en plus de `manage.py test`. Ajouter `pytest -v` comme commande recommandée. | Section Tests liste `pytest -v` et `python manage.py test`. | — | cc:完了 |
| 1.7 | **Ajouter la section Mobile (Flutter)** — Documenter l'existence de l'app Flutter (`../andd_baay_mobile`) : stack, prérequis (`flutter` CLI), commande de lancement. | README contient section "Application mobile" avec stack Flutter, commandes et prérequis. | — | cc:完了 |
| 1.8 | **Ajouter une section Dépannage** — Couvrir les erreurs fréquentes au premier démarrage : `.env` manquant, erreur de migration, absence de Redis, avertissements `check --deploy`. | Section Dépannage liste ≥ 3 scénarios d'erreur avec cause et solution. | 1.1, 1.2 | cc:完了 |

---

## Completed

Voir Phase 1 ci-dessus — 8/8 tâches `cc:完了` (2026-05-27).

## Archived

<!-- older completed tasks -->
