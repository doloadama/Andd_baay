# Plan — Onboarding par type de compte & coopératives par rôles

> Statut : **proposition à valider** (aucun code écrit). Décisions actées :
> coopérative = **entité dédiée** ; le fermier affilié **garde la propriété** de sa ferme ;
> on **valide ce plan avant** toute implémentation.

## 0. Principe directeur

On sépare deux notions aujourd'hui confondues :

| Notion | Question | Détermine | Porté par |
|---|---|---|---|
| **Type de compte** | « Qui suis-je en arrivant ? » | le **parcours** d'onboarding | `Profile.account_type` (nouveau) |
| **Rôle** (ferme / coop) | « Que puis-je faire ici ? » | les **permissions** | `MembreFerme.role`, `MembreCooperative.role` (nouveau) |

Le type de compte ne donne **aucun** droit en soi : il ne fait que **router** l'onboarding.
Les droits viennent toujours des rôles d'appartenance.

---

## 1. Modèle de données

### 1.1 `Profile.account_type` (nouveau champ)
```
account_type = CharField(choices=[
    ('fermier',     'Fermier indépendant'),   # défaut
    ('cooperative', 'Coopérative'),
    ('technicien',  'Technicien agricole'),
    ('ouvrier',     'Ouvrier agricole'),
], default='fermier')
```
- Migration : ajout avec `default='fermier'` → tous les comptes existants restent fermiers,
  comportement actuel inchangé.

### 1.2 `Cooperative` (nouveau modèle)
Calqué sur `Ferme` pour la cohérence (UUID, localisation, code d'accès) :
```
id (UUID), nom, description
pays / region / localite (FK, comme Ferme)
code_acces (unique, via generate_unique_code_acces — réutiliser le pattern Ferme)
date_creation, date_modification
# (subscription_tier coop : hors périmètre pour l'instant)
```
- Pas de FK `admin` directe : l'admin est défini par `MembreCooperative(role='admin')`
  (au moins un admin garanti à la création).

### 1.3 `MembreCooperative` (nouveau modèle)
Calqué sur `MembreFerme` :
```
cooperative (FK), utilisateur (FK Profile)
role = CharField(choices=[
    ('admin',          'Admin / Président'),
    ('gestionnaire',   'Gestionnaire'),
    ('technicien',     'Technicien coop'),
    ('consultant',     'Consultant'),
    ('fermier_affilie','Fermier affilié'),
])
peut_gerer_membres (bool)
statut (actif/suspendu), date_adhesion, date_expiration
unique_together = (cooperative, utilisateur)
```

### 1.4 `Ferme.cooperative` (nouveau FK)
```
cooperative = ForeignKey(Cooperative, null=True, blank=True,
                         on_delete=SET_NULL, related_name='fermes')
```
- **`proprietaire` reste inchangé** : le fermier affilié possède sa ferme.
  La coop y accède via la cascade de permissions (§3), sans en être propriétaire.
- Hypothèse : une ferme appartient à **au plus une** coopérative.

---

## 2. Parcours d'inscription (routage onboarding)

Après confirmation email + 1ʳᵉ connexion, si `account_type` non défini → **écran « Choix du profil »**.
Puis `onboarding_wizard_view` devient un **routeur** :

```
account_type == 'fermier'      → wizard actuel (ferme → projet → diagnostic) ⇒ PROPRIÉTAIRE
account_type == 'cooperative'  → wizard coop (créer Cooperative → rattacher/créer fermes → inviter)
account_type in (technicien,
                 ouvrier)      → écran « Rejoindre une ferme »
                                  (saisie code_acces OU invitations en attente)
                                  ⇒ MembreFerme(role=technicien|ouvrier)
```
- Le technicien/ouvrier **ne crée jamais de ferme** : il réutilise tel quel
  `code_acces` / `DemandeAccesFerme` / `rejoindre_ferme(token)`.
- « Plus tard » reste possible partout (`onboarding_complete_view`).

---

## 3. Permissions — cascade coopérative (`baay/permissions.py`)

### 3.1 Constantes & ensembles (nouveaux)
```
ROLE_COOP_ADMIN, ROLE_COOP_GESTIONNAIRE, ROLE_COOP_TECHNICIEN,
ROLE_COOP_CONSULTANT, ROLE_COOP_FERMIER_AFFILIE
```

### 3.2 Rôle effectif sur une ferme
Étendre `role_dans_ferme(profile, ferme)` :
1. Propriétaire de la ferme → `PROPRIETAIRE` (inchangé).
2. Membre direct de la ferme → son rôle `MembreFerme` (inchangé).
3. **Nouveau** : si `ferme.cooperative` et `profile` a un rôle coop dessus, dériver un
   rôle ferme « effectif » :
   | Rôle coop | Rôle ferme effectif |
   |---|---|
   | admin | MANAGER (gestion projets/membres de la ferme, **pas** suppression) |
   | gestionnaire | MANAGER |
   | technicien | TECHNICIEN |
   | consultant | CONSULTANT |
   | fermier_affilie | aucun droit sur les **autres** fermes (seulement la sienne) |
4. **Rôle retenu = le plus fort** entre direct et dérivé-coop.

> Garde-fou propriété : `peut_supprimer_ferme` **reste propriétaire-only**.
> Un admin coop gère mais ne supprime pas la ferme d'un membre.

### 3.3 Querysets accessibles
- `fermes_accessibles_qs(profile)` : ajouter les fermes des coops où le profil a un rôle
  de gestion/technique/consultant.
- `projets_accessibles_qs(profile)` : idem via `ferme__cooperative`.
- Nouveaux : `role_dans_cooperative(profile, coop)`, `cooperatives_accessibles_qs(profile)`,
  `roles_coop_assignables_par(role)` (qui invite/assigne quoi).

---

## 4. Vues / URLs

**Nouvelles**
- `choix_profil_view` (définit `account_type`)
- `creer_cooperative_view`, `cooperative_detail`, `cooperative_membres`
  (lister / inviter / assigner rôle / retirer), `rejoindre_cooperative`,
  `traiter_demande_acces_cooperative`
- Écran onboarding « rejoindre » pour technicien/ouvrier

**Modifiées**
- `onboarding_wizard_view` → routeur par `account_type`
- `dashboard_cooperative` → branché sur le **vrai** objet `Cooperative`
  (agrégation `cooperative.fermes` + KPIs multi-fermes)

---

## 5. Templates
- `onboarding/choix_profil.html` (cartes radio : Fermier / Coopérative / Technicien / Ouvrier)
- `onboarding/wizard_cooperative.html`
- `onboarding/rejoindre.html`
- `cooperatives/detail.html`, `cooperatives/membres.html`

---

## 6. Phasage (chaque phase = livrable testable)

| Phase | Contenu | Critère d'acceptation |
|---|---|---|
| **1** | `account_type` + écran choix + routeur onboarding + parcours technicien/ouvrier | Un compte technicien **ne voit jamais** « créer une ferme » ; il rejoint via code → devient membre technicien → dashboard. Fermier inchangé. |
| **2** | Modèles `Cooperative` / `MembreCooperative` + `Ferme.cooperative` + `creer_cooperative` | Un compte coop crée une coop, rattache/crée des fermes, les voit agrégées. |
| **3** | Gestion membres coop (inviter, rôles, `roles_coop_assignables_par`) | Un admin invite un gestionnaire/technicien qui obtient le bon accès. |
| **4** | Cascade permissions (`role_dans_ferme`, querysets coop-aware) | Technicien coop voit toutes les fermes de la coop ; admin gère les projets multi-fermes **mais ne supprime pas** la ferme d'un membre. |
| **5** | `dashboard_cooperative` branché + finitions UI | Dashboard coop affiche les vraies fermes/membres/KPIs agrégés. |

---

## 7. Migrations
1. `Profile.account_type` (`default='fermier'`, backfill implicite).
2. Création `Cooperative`, `MembreCooperative` ; ajout `Ferme.cooperative`.
- Aucune migration de données obligatoire : les propriétaires multi-fermes existants
  pourront créer une coop et y rattacher leurs fermes a posteriori.

## 8. Points encore à trancher
- Précédence exacte direct-vs-coop si conflit (proposé : rôle le plus fort).
- L'admin coop peut-il **créer** des projets sur la ferme d'un membre (proposé : oui, MANAGER) ?
- Une ferme dans plusieurs coops ? (proposé : non, une seule).
- Facturation/abonnement au niveau coop : **hors périmètre** pour l'instant.

## 9. Risques
- Toucher `permissions.py` impacte **toute** l'app → couvrir par des tests
  (`pytest baay/tests/`) avant/après §3.
- Bien isoler `account_type` (UX/routage) de la logique de droits (rôles) pour ne pas
  régresser les comptes existants.
