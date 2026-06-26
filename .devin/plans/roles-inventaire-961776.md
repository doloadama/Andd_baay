# Plan : Extension des rôles (Consultant/Invité) + Module Inventaire

Ajout des rôles temporaires CONSULTANT et INVITE à MembreFerme avec permissions granulaires, et création d'un module d'inventaire complet (intrants, récoltes, mouvements) lié aux investissements, avec UI DaisyUI/HTMX mobile-first.

---

## Tâche 1 : Rôles temporaires

### 1.1 Modèles (`baay/models.py`)

- Étendre `MembreFerme.ROLE_CHOICES` :
  - `('consultant', 'Consultant')`
  - `('invite', 'Invité')`
- Ajouter `date_expiration = models.DateTimeField(null=True, blank=True)` à `MembreFerme` (caractère temporaire).
- Ajouter `NoteAgronomique` : `projet (FK)`, `auteur (FK Profile)`, `contenu`, `date_creation`.

### 1.2 Permissions (`baay/permissions.py`)

- Ajouter `ROLE_CONSULTANT`, `ROLE_INVITE`.
- `ROLES_VISIBILITE_FERME` inclut les 2 nouveaux rôles.
- `ROLES_LECTURE_FINANCE` = `{proprietaire, manager, consultant}` (INVITE exclu).
- `ROLES_COMMENTAIRE` = `{proprietaire, manager, technicien, consultant}`.
- Mettre à jour `roles_assignables_par()`.
- Corriger le bug ligne 266 (return unreachable).

### 1.3 Services (`baay/core_services.py`)

- `transition_demande_acces()` : accepter `consultant`/`invite` dans la validation `role`.

### 1.4 Formulaires (`baay/forms.py`)

- `MembreFermeForm` : mettre à jour `choices` du champ `role`, ajouter `date_expiration` (DateTimeField optionnel).

### 1.5 Vues (`baay/views_fermes.py`, `baay/views.py`)

- `ajouter_membre_ferme` : persister `date_expiration` si fournie.
- `detail_ferme` : exposer `user_role` pour conditionner l'affichage.

### 1.6 Templates

- `detail_ferme.html` :
  - Afficher les nouveaux badges de rôle.
  - Badge "Accès temporaire" si `date_expiration` renseignée.
  - Cacher boutons d'édition/suppression pour consultant/invité.
  - Masquer section finance pour INVITE.
- `ajouter_membre.html` : champ `date_expiration` optionnel.

### 1.7 Tests (`baay/tests.py`)

- Tests d'ajout de membre consultant/invité.
- Tests de permissions : consultant lecture + commentaire ; invité lecture sans finance.

---

## Tâche 2 : Module Inventaire

### 2.1 Modèles (`baay/models.py`)

**StockIntrant**
- `ferme` (FK Ferme, related_name='intrants')
- `nom` (CharField, max 100)
- `categorie` (choices : `engrais`, `semence`, `pesticide`, `autre`)
- `quantite` (DecimalField, max_digits=12, decimal_places=2)
- `unite` (choices : `kg`, `L`, `sacs`, `unites`)
- `seuil_alerte` (DecimalField, default=10)
- `date_creation`, `date_modification` (auto)

**StockRecolte**
- `ferme` (FK Ferme, related_name='recoltes')
- `projet` (FK Projet, null=True, blank=True, related_name='recoltes')
- `produit` (FK ProduitAgricole)
- `quantite` (DecimalField)
- `unite` (choices : `kg`, `tonnes`, `sacs`)
- `date_recolte` (DateField)
- `qualite` (choices : `A`, `B`, `C`, `D`, `NC`)

**MouvementStock**
- `ferme` (FK Ferme)
- `type` (choices : `entree`, `sortie`)
- `stock_intrant` (FK StockIntrant, null=True)
- `stock_recolte` (FK StockRecolte, null=True)
- `quantite` (DecimalField, positive)
- `date_mouvement` (DateTimeField, auto_now_add)
- `raison` (CharField, max 255, blank=True)
- `utilisateur` (FK Profile, null=True)
- `investissement` (FK Investissement, null=True, blank=True)

### 2.2 Service métier (`baay/services/inventory_service.py`)

- `ajuster_stock_intrant(stock_id, delta, raison, user)` : atomique, crée MouvementStock.
- `ajuster_stock_recolte(stock_id, delta, raison, user)`.
- `stocks_en_alerte(ferme)` : StockIntrant avec `quantite < seuil_alerte`.
- `volume_total_recoltes(ferme)` : sum des quantités.
- `lier_investissement_a_stock(investissement)` : si `investissement.categorie == 'intrant'`, chercher/créer StockIntrant par nom (match fuzzy normalisé) et incrémenter.
- `historique_mouvements(ferme, limit=50)`.

### 2.3 Lien Finance ↔ Inventaire

- Signal `post_save` sur `Investissement` : si créé/maj et `categorie == 'intrant'`, appeler `inventory_service.lier_investissement_a_stock()`.
- Ou appel explicite dans la vue de création d'investissement pour plus de contrôle.

### 2.4 Admin (`baay/admin.py`)

- Enregistrer `StockIntrant`, `StockRecolte`, `MouvementStock` avec `ModelAdmin` (Unfold).
- Inline `MouvementStockInline` sur `StockIntrantAdmin`.

### 2.5 URLs (`baay/urls_fermes.py`)

Ajouter sous `/fermes/<uuid:ferme_id>/inventaire/` :
- `''` → `liste_inventaire`
- `'/intrants/ajouter/'` → `ajouter_intrant`
- `'/intrants/<uuid:intrant_id>/modifier/'` → `modifier_intrant`
- `'/intrants/<uuid:intrant_id>/ajuster/'` → `ajuster_intrant_htmx`
- `'/recoltes/ajouter/'` → `ajouter_recolte`
- `'/mouvements/'` → `liste_mouvements`

### 2.6 Vues (`baay/views_fermes.py` ou nouveau `baay/views_inventory.py`)

- `liste_inventaire(request, ferme_id)` : agrège intrants, récoltes, alertes, volume.
- `ajouter_intrant` / `modifier_intrant` : CRUD standard.
- `ajuster_intrant_htmx` : POST HTMX, appelle `inventory_service.ajuster_stock_intrant`, retourne fragment HTML mis à jour.
- `ajouter_recolte` : CRUD.
- `liste_mouvements` : liste paginée avec filtres.

### 2.7 Templates (nouveau dossier `templates/inventaire/`)

- `liste_inventaire.html` :
  - DaisyUI tabs : Intrants | Récoltes | Mouvements.
  - Bento Cards en haut :
    - Alertes stocks bas (badge rouge + liste)
    - Volume total récoltes (badge vert)
  - Table intrants avec colonne "Quantité" éditable via HTMX (boutons +/- ou input inline).
  - Table récoltes avec filtre par qualité.
  - Responsive : scroll horizontal sur tables, cards empilées en mobile.
- Fragments HTMX :
  - `_intrant_row.html` (ligne de table mise à jour).
  - `_alertes_stock.html` (bento card alertes).

### 2.8 Bento Card Dashboard Ferme

- Dans `detail_ferme.html`, ajouter une card "Inventaire" affichant :
  - Nombre d'alertes stocks bas (lien vers onglet intrants).
  - Volume total récoltes (lien vers onglet récoltes).

### 2.9 Permissions

- `peut_voir_inventaire(profile, ferme)` : consultant + tous les rôles gestion.
- `peut_modifier_inventaire(profile, ferme)` : propriétaire, manager.
- Appliquer dans les vues via `login_required` + check manuel.

---

## Livrables attendus

| Fichier | Action |
|---|---|
| `baay/models.py` | + rôles, + date_expiration, + 3 modèles inventaire, + NoteAgronomique |
| `baay/permissions.py` | + constants, + fonctions, fix bug ligne 266 |
| `baay/forms.py` | + choix rôles, + date_expiration |
| `baay/core_services.py` | + rôles dans validation demande |
| `baay/services/inventory_service.py` | **Nouveau** |
| `baay/admin.py` | + 3 ModelAdmin inventaire |
| `baay/urls_fermes.py` | + routes inventaire |
| `baay/views_fermes.py` | + vues membres (date_exp), + vues inventaire |
| `baay/views_finance.py` | hook investissement → stock |
| `templates/fermes/detail_ferme.html` | badges rôles, masquage selon permissions, card inventaire |
| `templates/fermes/ajouter_membre.html` | champ date_expiration |
| `templates/inventaire/liste_inventaire.html` | **Nouveau** + fragments HTMX |
| `baay/tests.py` | + tests rôles, + tests inventaire |
| Migrations | `makemigrations baay` → commit |

---

## Questions résolues

- **Consultant comments** : nouvelle entité `NoteAgronomique` liée à `Projet`, visible par tout le monde, créable par consultant + rôles gestion.
- **Intrant matching** : auto-match par nom normalisé (strip, lower, sans accents) dans `inventory_service.lier_investissement_a_stock`. Pas de FK ajoutée à `Investissement`.
- **Récolte source** : `StockRecolte` lié à `Ferme` + `Projet` optionnel (nullable), permettant de tracer l'origine d'une récolte tout en gardant l'agrégation au niveau ferme.
