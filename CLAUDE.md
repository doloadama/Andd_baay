# Andd Baay — CLAUDE.md

Plateforme web de gestion agricole collaborative pour exploitations sahéliennes.
Django monolithe modulaire + Flutter mobile + API REST.

## Stack

| Couche | Tech |
|--------|------|
| Backend | Django 5, DRF, Django Channels + Daphne |
| DB | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Django Templates, Bootstrap 5, JS vanilla, PWA |
| IA | Scikit-learn (`modele_rendement.pkl`) |
| Mobile | Flutter (`/andd_baay_mobile`) |
| Déploiement | Docker, Render, Vercel, Railway |

## Layout

```
Andd_Baayi/      Django settings, urls, asgi, wsgi
baay/            App principale (models, views_*.py, urls_*.py, services.py, permissions.py)
baay/consumers.py  WebSocket consumers (Chat, Inbox)
templates/       Templates Django
baay/static/     CSS, JS, icônes
locale/          i18n (fr/wo)
```

## Commandes clés

```bash
python manage.py runserver          # Serveur dev HTTP
python manage.py migrate            # Migrations DB
python manage.py test               # Tests Django
pytest                              # Tests pytest
daphne Andd_Baayi.asgi:application  # Serveur ASGI (WebSocket)
```

## Conventions

- **Rôles** : `owner`, `manager`, `technician`, `worker` — centralisés dans `baay/permissions.py`
- **Vues** : modularisées par domaine (`views_farm.py`, `views_project.py`, `views_messaging.py`, etc.)
- **API mobile** : serializers avec alias Flutter dans `baay/serializers_mobile.py`
- **WebSocket** : schéma versionné dans `baay/messaging_contract.py`
- **Langue** : interface en français, code en anglais

## Tests

```bash
pytest                  # Suite complète
pytest baay/tests/      # Tests app principale
python manage.py test baay
```

## Déploiement

- `railway.toml` / `render.yaml` — configs cloud
- `dockerfile` + `docker-compose.yml` — local/prod Docker
- `Procfile` — Heroku/Railway process types
- Vercel (`vercel.json`) pour assets statiques
