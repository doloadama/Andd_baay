# Andd Baay

**Plateforme web de gestion agricole collaborative** — fermes, projets, semis, tâches, messagerie temps réel et prévisions de rendement.

> Conçue pour les exploitations sahéliennes : multi-rôles (propriétaire, manager, technicien, ouvrier), workflows agronomiques, communication d'équipe instantanée, et prédictions de rendement basées sur des règles métier.

---

## Stack technique

| Couche                | Technologies                                                                      |
| --------------------- | --------------------------------------------------------------------------------- |
| Backend HTTP          | Django 5, Django REST Framework, django-allauth (email + Google OAuth)            |
| Temps réel (WebSocket)| Django Channels + Daphne, `InMemoryChannelLayer` (dev) / `channels-redis` (prod)  |
| Base de données       | SQLite (dev) — PostgreSQL (prod, recommandé)                                      |
| Frontend              | Django Templates, Bootstrap 5, JavaScript vanilla, PWA (manifest + service worker)|
| IA / prévisions       | Scikit-learn (`modele_rendement.pkl`) + règles métier (`baay/services.py`)        |
| Déploiement           | Docker / docker-compose, Render, Vercel                                           |

---

## Architecture du dépôt

```
Andd_Baayi/        Configuration Django (settings, urls, asgi, wsgi)
baay/              Application principale
  models.py        Données : Profile, Ferme, Projet, Semis, Tâche, Conversation, Message…
  views_*.py       Vues HTTP modularisées par domaine
  urls_*.py        URL routing par domaine
  consumers.py     Consumers Channels (ChatConsumer, InboxConsumer)
  routing.py       Routing WebSocket
  messaging_contract.py   Schéma canonique des événements WS (versionnés)
  permissions.py   Politique de rôles centralisée
  services.py      Logique métier + prédiction de rendement
  signals.py       Signaux Django (création de profil, etc.)
  migrations/      Migrations DB (incluant `0022_participation_conversation`)
templates/         Templates Django (incluant partials messagerie)
baay/static/       CSS, JS, icônes, images
```

L'architecture suit un monolithe modulaire : un seul projet Django avec une séparation stricte par **domaines fonctionnels** (auth, fermes, projets, semis, tâches, messagerie, API).

---

## Démarrage rapide

### Pré-requis

- Python 3.12
- (Optionnel) Redis si vous voulez tester le `channels-redis` layer
- (Optionnel) Docker + docker-compose

### Installation locale

```bash
# 1. Cloner et entrer dans le dépôt
git clone <url-du-depot>
cd Andd_baay

# 2. Créer un environnement virtuel
python -m venv env
# Windows :   .\env\Scripts\activate
# Linux/Mac : source env/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Variables d'environnement (cf. `.env.example`)
cp .env.example .env
# Editez .env et fournissez au minimum DJANGO_SECRET_KEY

# 5. Migrations
python manage.py migrate

# 6. (Optionnel) Créer un superutilisateur
python manage.py createsuperuser

# 7. Lancer le serveur (Daphne via runserver)
python manage.py runserver
```

L'application est disponible sur <http://localhost:8000>.

### Avec Docker

```bash
docker compose up --build
```

---

## Variables d'environnement

| Variable                  | Description                                                  | Défaut       |
| ------------------------- | ------------------------------------------------------------ | ------------ |
| `DJANGO_SECRET_KEY`       | Clé secrète Django (obligatoire)                             | —            |
| `DEBUG`                   | Mode debug Django                                            | `False`      |
| `ALLOWED_HOSTS`           | Hôtes autorisés (séparés par virgule)                        | `localhost`  |
| `DATABASE_URL`            | URL PostgreSQL en production                                 | SQLite local |
| `REDIS_URL`               | Si défini, active `channels-redis` pour les WebSockets       | _(vide)_     |
| `GOOGLE_OAUTH_CLIENT_ID`  | OAuth Google (login social)                                  | _(vide)_     |
| `GOOGLE_OAUTH_SECRET`     | OAuth Google                                                 | _(vide)_     |
| `EMAIL_HOST` / `EMAIL_*`  | Configuration SMTP                                           | console (dev)|

Cf. `.env.example` pour la liste exhaustive.

---

## Fonctionnalités principales

### Authentification & rôles
- Connexion email/mot de passe et Google OAuth via `django-allauth`
- Rôles par ferme : **propriétaire**, **manager**, **technicien**, **ouvrier**
- Politique de permissions centralisée dans `baay/permissions.py`

### Gestion agricole
- Fermes multi-membres avec **codes d'accès** et demandes de rejoindre
- Projets agricoles, semis, investissements
- Tâches hiérarchisées par rôle, suivi d'avancement

### Messagerie temps réel
- Conversations 1-à-1 et groupes (`Conversation` avec `through`-model `ParticipationConversation`)
- WebSockets via Channels : nouveaux messages, accusés de lecture, indicateur de saisie, badges non-lus en direct
- **Drawer desktop** glissant + page mobile plein écran ; deep-link depuis la cloche de notifications
- Pièces jointes, réponses (reply-to), réactions emoji
- Idempotence d'envoi (`client_message_id`) et resync sur reconnexion
- Contrats d'événements WS versionnés (`baay/messaging_contract.py`)

### Prévisions de rendement
- Service `baay/services.py` combinant un modèle Scikit-learn (`modele_rendement.pkl`) et des règles agronomiques
- Indice de confiance retourné avec chaque prédiction

### PWA
- Manifeste, icônes, service worker (`baay/static/js/sw.js`) : installation sur mobile et utilisation hors-ligne basique

---

## Tests

```bash
python manage.py test
```

Les tests couvrent le domaine principal dans `baay/tests.py`.

---

## Déploiement

| Cible    | Fichier                       | Notes                                                  |
| -------- | ----------------------------- | ------------------------------------------------------ |
| Docker   | `dockerfile`, `docker-compose.yml` | Image Python 3.12 + Gunicorn ; collectstatic au build |
| Render   | `render.yaml`                 | `gunicorn Andd_Baayi.wsgi:application`                 |
| Vercel   | `vercel.json`, `build_files.sh` | Pour déploiement serverless (HTTP uniquement, pas de WS) |

> **Important pour le temps réel** : Vercel ne supporte pas WebSocket. Utilisez Render, Docker ou tout autre runtime ASGI persistant pour les fonctionnalités messagerie temps réel.

---

## Conventions de code

- **Vues** : modularisées par domaine (`views_messagerie.py`, `views_fermes.py`, …) re-exportant depuis le `views.py` central pour rétro-compatibilité
- **URLs** : idem (`urls_messagerie.py`, `urls_fermes.py`, …)
- **Permissions** : toute vérification de rôle passe par `baay/permissions.py`
- **Événements WebSocket** : construits via les builders versionnés de `messaging_contract.py` (jamais directement)
- **Frontend JS messagerie** : exposé via `window.initMessagerieInbox()` / `window.initMessagerieConversation()` (idempotents, ré-invocables — nécessaire pour le chargement dynamique du drawer)

---

## Licence

Projet privé. Tous droits réservés.
