# Andd Baay

Plateforme web Django pour la gestion agricole collaborative: fermes, projets, semis, tâches, messagerie temps réel et prévisions de rendement.

## Stack technique

- Backend: Django, Django REST Framework, django-allauth
- Temps réel: Channels + Daphne (WebSocket)
- Données: SQLite (dev) / PostgreSQL (prod)
- Frontend: Django Templates + assets statiques
- IA métier: services Python de prévision (`baay/services.py`)

## Architecture

- Configuration projet: `Andd_Baayi/`
- Domaine principal: `baay/` (models, permissions, services, views, urls, signals)
- Templates: `templates/`
- Assets statiques: `baay/static/`

Le projet suit une architecture monolithique modulaire avec séparation par domaines fonctionnels (auth, projets, fermes, tâches, messagerie, API).

## Démarrage rapide

1. Créer et activer un environnement virtuel.
2. Installer les dépendances:

```bash
pip install -r requirements.txt
```

3. Définir les variables d'environnement (minimum: `DJANGO_SECRET_KEY`).
4. Appliquer les migrations:

```bash
python manage.py migrate
```

5. Lancer le serveur:

```bash
python manage.py runserver
```

## Fonctionnalités principales

- Authentification email/mot de passe + Google OAuth
- Gestion des fermes et rôles (propriétaire, manager, technicien, ouvrier)
- Gestion de projets agricoles, semis et investissements
- Gestion de tâches hiérarchisées par rôle
- Messagerie d'équipe en temps réel avec WebSocket
- Prévisions de rendement basées sur des règles agronomiques

## Qualité et tests

Exécuter la suite de tests:

```bash
python manage.py test
```
