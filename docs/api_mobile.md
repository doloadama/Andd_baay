# API Mobile — Andd Baay

Base URL: `/api/v1/` (nouveaux endpoints)  
Base URL legacy: `/api/mobile/` (endpoints existants)  
Auth: `Authorization: Bearer <access_token>` (JWT) sur tous les endpoints sauf login/register.

---

## Authentification

### POST /api/token/ — Obtenir un token JWT

```
POST /api/token/
Content-Type: application/json

{
  "username": "mamadou",
  "password": "motdepasse123"
}
```

**Réponse 200 :**
```json
{
  "access": "eyJ0eXAiOiJKV1Qi...",
  "refresh": "eyJ0eXAiOiJKV1Qi..."
}
```

### POST /api/token/refresh/ — Renouveler le token

```
POST /api/token/refresh/
Content-Type: application/json

{ "refresh": "<refresh_token>" }
```

**Réponse 200 :** `{ "access": "<nouveau_access_token>" }`

### POST /api/mobile/auth/register/ — Créer un compte

```
POST /api/mobile/auth/register/
Content-Type: application/json

{
  "username": "mamadou",
  "email": "mamadou@exemple.sn",
  "first_name": "Mamadou",
  "last_name": "Diallo",
  "password": "motdepasse123",
  "password2": "motdepasse123",
  "phone_number": "+221771234567"
}
```

**Réponse 201 :**
```json
{
  "access": "eyJ0eXAi...",
  "refresh": "eyJ0eXAi...",
  "user": { "id": 1, "username": "mamadou", "email": "mamadou@exemple.sn" }
}
```

---

## Profil utilisateur

### GET /api/v1/profile/ — Profil de l'utilisateur connecté

```
GET /api/v1/profile/
Authorization: Bearer <token>
```

**Réponse 200 :**
```json
{
  "id": "a1b2c3d4-...",
  "user": {
    "id": 1,
    "username": "mamadou",
    "email": "mamadou@exemple.sn",
    "first_name": "Mamadou",
    "last_name": "Diallo"
  },
  "phone_number": "+221771234567",
  "address": "Dakar, Sénégal"
}
```

### GET /api/mobile/auth/me/ — Alias (profil + mise à jour)

```
GET  /api/mobile/auth/me/
PATCH /api/mobile/auth/me/
Authorization: Bearer <token>
```

**PATCH body :** `{ "phone_number": "+221779999999", "first_name": "Ibrahima" }`

---

## Fermes

### GET /api/mobile/fermes/ — Lister les fermes

```
GET /api/mobile/fermes/
Authorization: Bearer <token>
```

**Réponse 200 :**
```json
[
  {
    "id": "f1a2b3c4-...",
    "nom": "Ferme de Thiès",
    "description": "Cultures de mil et arachide",
    "superficie_totale": "15.50",
    "localite_nom": "Thiès",
    "subscription_tier": "basic",
    "is_premium": false,
    "nb_projets": 3,
    "image_couverture_url": null,
    "date_creation": "2025-01-15T10:30:00Z"
  }
]
```

### POST /api/mobile/fermes/ — Créer une ferme

```
POST /api/mobile/fermes/
Authorization: Bearer <token>
Content-Type: application/json

{
  "nom": "Ferme Koliabé",
  "description": "Grande exploitation maraîchère",
  "superficie_totale": "20.00",
  "latitude": 14.6928,
  "longitude": -17.4467
}
```

**Réponse 201 :** objet Ferme complet (FermeDetailSerializer)

### GET /api/mobile/fermes/<uuid:ferme_id>/ — Détail d'une ferme

```
GET /api/mobile/fermes/f1a2b3c4-.../
Authorization: Bearer <token>
```

**Réponse 200 :** objet Ferme avec liste de projets imbriqués.

---

## Projets agricoles

### GET /api/mobile/fermes/<uuid>/projets/ — Projets d'une ferme

```
GET /api/mobile/fermes/<ferme_id>/projets/?statut=en_cours
Authorization: Bearer <token>
```

**Paramètres query :** `statut` (en_cours | en_pause | fini | cloture)

**Réponse 200 :**
```json
[
  {
    "id": "p1a2b3c4-...",
    "nom": "Campagne Mil 2025",
    "statut": "en_cours",
    "type_cycle": "campagne",
    "superficie": "5.00",
    "date_lancement": "2025-06-01",
    "date_fin": "2025-11-30",
    "localite_nom": "Thiès",
    "taux_avancement": 42,
    "avancement": 42,
    "nb_produits": 2,
    "image_fond_url": null
  }
]
```

### POST /api/mobile/fermes/<uuid>/projets/ — Créer un projet

```
POST /api/mobile/fermes/<ferme_id>/projets/
Authorization: Bearer <token>
Content-Type: application/json

{
  "nom": "Campagne Arachide 2025",
  "localite_id": "<uuid_localite>",
  "superficie": "8.00",
  "date_lancement": "2025-07-01",
  "date_fin": "2025-12-31",
  "type_cycle": "campagne",
  "type_irrigation": "Aucune",
  "type_engrais": "Organique",
  "budget_alloue": "500000"
}
```

**Réponse 201 :** objet Projet complet (ProjetDetailSerializer)

### GET /api/mobile/projets/<uuid:projet_id>/ — Détail d'un projet

```
GET /api/mobile/projets/<projet_id>/
Authorization: Bearer <token>
```

---

## Tâches

### GET /api/v1/taches/ — Lister les tâches

```
GET /api/v1/taches/?ferme=<uuid>&projet=<uuid>
Authorization: Bearer <token>
```

**Réponse 200 :**
```json
[
  {
    "id": "t1a2b3c4-...",
    "titre": "Arroser les plants de tomate",
    "description": "Arrosage goutte-à-goutte",
    "statut": "a_faire",
    "priorite": "haute",
    "date_echeance": "2025-07-15",
    "date_creation": "2025-07-01T08:00:00Z",
    "assigne_a_nom": "Ibrahima Diallo",
    "assigne_par_nom": "Mamadou Fall",
    "est_en_retard": false,
    "ferme": "f1a2b3c4-...",
    "projet": "p1a2b3c4-..."
  }
]
```

### POST /api/v1/taches/ — Créer une tâche

```
POST /api/v1/taches/
Authorization: Bearer <token>
Content-Type: application/json

{
  "titre": "Récolte des arachides",
  "description": "Récolte manuelle parcelle nord",
  "statut": "a_faire",
  "priorite": "urgente",
  "date_echeance": "2025-11-20",
  "ferme": "<uuid_ferme>",
  "projet": "<uuid_projet>",
  "assigne_a": "<uuid_profile>"
}
```

**Réponse 201 :** objet Tâche complet

### PATCH /api/v1/taches/<uuid>/statut/ — Mettre à jour le statut

```
PATCH /api/v1/taches/<task_id>/statut/
Authorization: Bearer <token>
Content-Type: application/json

{
  "statut": "en_cours",
  "commentaire_retour": "Commencé ce matin à 7h"
}
```

**Réponse 200 :** objet Tâche mis à jour

---

## Commentaires

### GET /api/v1/commentaires/<ct_label>/<uuid>/ — Lister les commentaires

```
GET /api/v1/commentaires/ferme/<ferme_id>/
GET /api/v1/commentaires/tache/<tache_id>/
GET /api/v1/commentaires/projet/<projet_id>/
Authorization: Bearer <token>
```

**ct_label** : `ferme`, `tache`, ou `projet`

**Réponse 200 :**
```json
[
  {
    "id": "c1a2b3c4-...",
    "texte": "Bon avancement sur ce champ !",
    "auteur_nom": "Mamadou Fall",
    "auteur_username": "mamadou",
    "created_at": "2025-07-10T14:30:00Z"
  }
]
```

### POST /api/v1/commentaires/<ct_label>/<uuid>/ — Créer un commentaire

```
POST /api/v1/commentaires/ferme/<ferme_id>/
Authorization: Bearer <token>
Content-Type: application/json

{ "texte": "Les cultures sont en bonne santé." }
```

**Réponse 201 :** objet Commentaire créé

---

## Prévisions de récolte

### GET /api/v1/previsions/ — Prévisions par projet

```
GET /api/v1/previsions/?projet=<uuid>
Authorization: Bearer <token>
```

**Réponse 200 :**
```json
[
  {
    "rendement_estime_min": 800.0,
    "rendement_estime_max": 1200.0,
    "indice_confiance": 78.5,
    "rendement_min": 800.0,
    "rendement_max": 1200.0,
    "confiance": 78.5,
    "source_rendement": null,
    "date_recolte_prevue": "2025-11-30",
    "date_prediction": "2025-07-01T09:00:00Z"
  }
]
```

---

## Diagnostic phytosanitaire (async)

### POST /api/v1/diagnostic/ — Soumettre une image

```
POST /api/v1/diagnostic/
Authorization: Bearer <token>
Content-Type: multipart/form-data

photo=<fichier_image>
culture=mil
langue=fr
```

**Paramètres :**
- `photo` : fichier JPEG / PNG / WebP, max 10 Mo (requis)
- `culture` : clé culture (`mil`, `arachide`, `sorgho`, `mais`, `riz`, etc.)
- `langue` : `fr` (français) ou `wo` (wolof), défaut `fr`

**Réponse 202 :**
```json
{ "task_id": "8f3a1b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c" }
```

### GET /api/v1/diagnostic/<task_id>/ — Récupérer le résultat (polling)

```
GET /api/v1/diagnostic/8f3a1b2c-.../
Authorization: Bearer <token>
```

**Réponse en attente (200) :**
```json
{ "status": "pending" }
```

**Réponse terminée (200) :**
```json
{
  "status": "done",
  "result": {
    "maladie": "Mildiou",
    "confiance": 0.87,
    "conseils": "Appliquer un fongicide à base de cuivre...",
    "culture": "Tomate"
  }
}
```

**Réponse erreur (200) :**
```json
{ "status": "error", "error": "Analyse impossible : image de mauvaise qualité." }
```

**Réponse expirée (410) :**
```json
{ "status": "expired", "detail": "Résultat expiré ou introuvable." }
```

---

## Codes d'erreur fréquents

| Code | Signification |
|------|---------------|
| 200  | Succès |
| 201  | Ressource créée |
| 202  | Requête acceptée (async) |
| 400  | Données invalides (voir corps de la réponse) |
| 401  | Non authentifié |
| 403  | Accès refusé |
| 404  | Ressource introuvable |
| 410  | Résultat expiré |
| 415  | Format de fichier non supporté |
| 429  | Trop de requêtes (rate limit) |
