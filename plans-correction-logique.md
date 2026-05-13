# Plan de correction de la logique fermes/membres/projets/produits

Clarifier la règle propriétaire, sécuriser la création de projet et ajouter un vrai flux produit.

---

## Partie 1 : Clarifier propriétaire vs MembreFerme

**Fichiers** : `baay/models.py`, `baay/permissions.py`, `baay/tests.py`

1. **Supprimer** `'proprietaire'` de `MembreFerme.ROLE_CHOICES` dans `models.py`. Le vrai propriétaire est uniquement `Ferme.proprietaire`.
2. **Corriger** `peut_modifier_budget_ferme()` dans `permissions.py` pour accepter aussi `ferme.proprietaire` sans exiger de ligne membre.
3. **Mettre à jour** les tests dans `tests.py` qui attendent `MembreFerme(role='proprietaire')` — remplacer par assertion sur `Ferme.proprietaire`.

---

## Partie 2 : Sécuriser la création de projet

**Fichiers** : `baay/forms.py`, `baay/views.py`

1. **ProjetForm** : filtrer le queryset de `ferme` via `peut_creer_projet(profile, ferme)`, pas seulement `fermes_accessibles_qs`.
2. **Vue `creer_projet`** : après `form.is_valid()`, revérifier `peut_creer_projet(request.user.profile, projet.ferme)` avant de sauvegarder.
3. **ProjetForm** : rendre `produits_selection` `required=True`, ou attacher l’erreur globale au champ pour meilleure UX.
4. **ProjetForm `clean()`** : en mode superficie par produit, stocker automatiquement `superficie_allouee = projet.superficie / len(produits)` dans chaque `ProjetProduit` créé.

---

## Partie 3 : Flux produit après création de projet

**Fichiers** : `baay/urls.py`, `baay/views.py`, `baay/forms.py`, `templates/projets/`

1. **Créer** une nouvelle vue `ajouter_projet_produit(request, projet_id)` accessible aux rôles techniques.
2. **Créer** un formulaire `AjouterProduitProjetForm` qui sélectionne un `ProduitAgricole` existant + superficie_allouee + date_semis.
3. **Valider** `unique_together(projet, produit)` pour éviter les doublons.
4. **Ajouter** une URL `/projets/<uuid:projet_id>/produits/ajouter/`.
5. **Ajouter** un bouton **“Ajouter un produit”** dans `detail_projet.html`.

---

## Ordre d’exécution recommandé

1. Partie 1 (modèle + permissions)
2. Partie 2 (formulaire + vue projet)
3. Partie 3 (formulaire + vue + template produit)
4. Tests
