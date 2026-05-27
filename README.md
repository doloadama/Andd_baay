# Andd Baay

**Plateforme web de gestion agricole collaborative** — fermes, projets, semis, tâches, messagerie temps réel et prévisions de rendement.

> Conçue pour les exploitations sahéliennes : multi-rôles (propriétaire, manager, technicien, ouvrier), workflows agronomiques, communication d'équipe instantanée, et prédictions de rendement basées sur des règles métier.

---

## Démarrage rapide

### Prérequis

- **Python 3.12** (version fixée dans `.python-version` — utilisez [pyenv](https://github.com/pyenv/pyenv) ou installez Python 3.12 directement)
- (Optionnel) Redis si vous voulez tester le layer `channels-redis` en production
- (Optionnel) Docker + docker-compose

### Installation locale

```bash
# 1. Cloner le dépôt
git clone https://github.com/<votre-compte>/andd-baay.git
cd Andd_baay

# 2. Créer un environnement virtuel
python -m venv env
# Windows :   .\env\Scripts\activate
# Linux/Mac : source env/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# Pour contribuer (tests + debug toolbar) :
pip install -r requirements-dev.txt

# 4. Variables d'environnement
cp .env.example .env
# Éditez .env : fournissez au minimum DJANGO_SECRET_KEY=une-valeur-secrete

# 5. Migrations
python manage.py migrate

# 6. Créer un utilisateur admin (pour se connecter immédiatement)
python manage.py createsuperuser
# Exemple : Email → admin@example.com / Mot de passe → changeme123
# Vous pourrez vous connecter sur http://localhost:8000/admin/ avec ces identifiants.

# 7. Lancer le serveur
python manage.py runserver
```

### Vérifier que tout fonctionne

Après `runserver`, ouvrez **<http://localhost:8000>**.
Vous devez voir la page de connexion Andd Baay. Connectez-vous avec le compte créé à l'étape 6.

Pour valider la configuration Django :
```bash
python manage.py check
```

### Avec Docker

```bash
docker compose up --build
```

---

## Variables d'environnement

| Variable                  | Description                                                  | Défaut       |
| ------------------------- | ------------------------------------------------------------ | ------------ |
| `DJANGO_SECRET_KEY`       | Clé secrète Django **(obligatoire)**                         | —            |
| `DEBUG`                   | Mode debug Django                                            | `False`      |
| `ALLOWED_HOSTS`           | Hôtes autorisés (séparés par virgule)                        | `localhost`  |
| `DATABASE_URL`            | URL PostgreSQL en production                                 | SQLite local |
| `REDIS_URL`               | Si défini, active `channels-redis` pour les WebSockets       | _(vide)_     |
| `GOOGLE_CLIENT_ID`        | OAuth Google (login social)                                  | _(vide)_     |
| `GOOGLE_CLIENT_SECRET`    | OAuth Google                                                 | _(vide)_     |
| `GEMINI_API_KEY`          | Chatbot + analyse photo maladies des plantes                 | _(vide)_     |
| `OPENWEATHER_API_KEY`     | Météo des fermes                                             | _(vide)_     |
| `EMAIL_HOST` / `EMAIL_*`  | Configuration SMTP (console en dev si vide)                  | console      |

Cf. `.env.example` pour la liste exhaustive et les instructions d'obtention.

---

## Stack technique

| Couche                 | Technologies                                                                     |
| ---------------------- | -------------------------------------------------------------------------------- |
| Backend HTTP           | Django 5, Django REST Framework, django-allauth (email + Google OAuth)           |
| Temps réel (WebSocket) | Django Channels + Daphne, `InMemoryChannelLayer` (dev) / `channels-redis` (prod) |
| Base de données        | SQLite (dev) — PostgreSQL (prod, recommandé)                                     |
| Frontend               | Django Templates, Bootstrap 5, JavaScript vanilla, PWA (manifest + service worker)|
| IA / prévisions        | Scikit-learn (`modele_rendement.pkl`) + règles métier (`baay/services.py`)        |
| Mobile                 | Flutter (`../andd_baay_mobile`) — voir [Application mobile](#application-mobile) |
| Déploiement            | Docker / docker-compose, Render, Vercel, Railway                                 |

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
  migrations/      Migrations DB
templates/         Templates Django (incluant partials messagerie)
baay/static/       CSS, JS, icônes, images
locale/            Fichiers de traduction (fr, wo)
```

L'architecture suit un monolithe modulaire : un seul projet Django avec une séparation stricte par **domaines fonctionnels** (auth, fermes, projets, semis, tâches, messagerie, API).

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
- Conversations 1-à-1 et groupes
- WebSockets via Channels : nouveaux messages, accusés de lecture, indicateur de saisie, badges non-lus en direct
- Drawer desktop glissant + page mobile plein écran ; deep-link depuis la cloche de notifications
- Pièces jointes, réponses (reply-to), réactions emoji
- Idempotence d'envoi (`client_message_id`) et resync sur reconnexion
- Contrats d'événements WS versionnés (`baay/messaging_contract.py`)

### Prévisions de rendement
- Service `baay/services.py` combinant un modèle Scikit-learn (`modele_rendement.pkl`) et des règles agronomiques
- Indice de confiance retourné avec chaque prédiction

### PWA
- Manifeste, icônes, service worker (`baay/static/js/sw.js`) : installation sur mobile et utilisation hors-ligne basique

---

## Application mobile

Le projet comprend une application Flutter native dans le répertoire `../andd_baay_mobile` (dépôt séparé ou dossier frère).

**Prérequis** : Flutter SDK installé ([flutter.dev/docs/get-started](https://docs.flutter.dev/get-started/install))

```bash
# Depuis le répertoire de l'app mobile
cd ../andd_baay_mobile

# Installer les dépendances
flutter pub get

# Lancer sur émulateur ou appareil connecté
flutter run

# Vérifier l'absence d'erreurs
flutter analyze
```

L'app mobile consomme l'API REST exposée par le backend Django (DRF). Assurez-vous que le serveur backend est en cours d'exécution et que l'URL de l'API est correctement configurée dans `lib/`.

---

## Tests

```bash
# Avec pytest (recommandé — couverture complète)
pytest -v

# Avec le runner Django
python manage.py test

# Tests d'un module spécifique
pytest baay/tests/ -v
```

`requirements-dev.txt` installe `pytest`, `pytest-django` et `django-debug-toolbar`.

---

## Déploiement

| Cible    | Fichier                            | Notes                                                         |
| -------- | ---------------------------------- | ------------------------------------------------------------- |
| Docker   | `dockerfile`, `docker-compose.yml` | Image Python 3.12 + Gunicorn ; `collectstatic` au build       |
| Render   | `render.yaml`                      | `gunicorn Andd_Baayi.wsgi:application`                        |
| Railway  | `railway.toml`                     | Déploiement automatique depuis la branche principale          |
| Vercel   | `vercel.json`, `build_files.sh`    | Pour déploiement serverless (HTTP uniquement, **pas de WS**)  |

> **Important pour le temps réel** : Vercel ne supporte pas WebSocket. Utilisez Render, Railway, Docker ou tout autre runtime ASGI persistant pour les fonctionnalités messagerie temps réel.

---

## Conventions de code

- **Vues** : modularisées par domaine (`views_messagerie.py`, `views_fermes.py`, …) re-exportant depuis `views.py` central
- **URLs** : idem (`urls_messagerie.py`, `urls_fermes.py`, …)
- **Permissions** : toute vérification de rôle passe par `baay/permissions.py`
- **Événements WebSocket** : construits via les builders versionnés de `messaging_contract.py` (jamais directement)
- **Frontend JS messagerie** : exposé via `window.initMessagerieInbox()` / `window.initMessagerieConversation()` (idempotents, ré-invocables)

---

## Dépannage

### `.env` introuvable ou `DJANGO_SECRET_KEY` manquant

```
django.core.exceptions.ImproperlyConfigured: SECRET_KEY...
```

**Solution** : copiez `.env.example` vers `.env` et renseignez `DJANGO_SECRET_KEY`.

```bash
cp .env.example .env
# Puis éditez .env : DJANGO_SECRET_KEY=une-valeur-longue-et-aleatoire
```

### Erreur de migration (`OperationalError: no such table`)

**Solution** : appliquez les migrations avant de lancer le serveur.

```bash
python manage.py migrate
```

### WebSocket / messagerie ne fonctionne pas

Si vous voyez `InMemoryChannelLayer` en dev, c'est normal — il ne supporte pas plusieurs processus.
En production, configurez `REDIS_URL` pour activer `channels-redis`.

```bash
# Vérifier que Redis tourne
redis-cli ping  # doit répondre PONG
# Puis dans .env :
# REDIS_URL=redis://localhost:6379/0
```

### `python manage.py check` retourne des avertissements

Ignorez les avertissements `--deploy` en développement local. En production, consultez la [checklist Django](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/).

---

## Licence

Projet privé. Tous droits réservés.
