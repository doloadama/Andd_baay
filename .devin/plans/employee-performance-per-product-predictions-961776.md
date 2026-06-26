# Plan: Employee Performance Dashboard + Per-Product Predictions

Ajouter une section productivite des employes au tableau de performance et afficher les predictions IA par produit dans le detail projet.

---

## 1. Employee Performance Section (`performance` view + template)

**Metriques choisies (par defaut, coherentes) :**
- **Taches terminees** — volume total par agent
- **Taux de completion a l'echeance** — % de taches terminees avant ou le jour de l'echeance
- **Taches en retard** — taches non terminees dont l'echeance est depassee
- **Score global** — ponderation simple : 60% taux a l'echeance + 40% volume normalise

**Scope :** filtrable par ferme (meme mecanisme que le reste du dashboard), avec fallback sur toutes les fermes accessibles.

**Fichiers concernes :**
- `baay/views.py` — fonction `performance()` : ajouter l'agregation des taches par `assigne_a`
- `templates/projets/performance.html` — nouvelle section "Agents les plus productifs" (tableau + mini-cartes)
- `static/css/performance.css` — styles responsive pour la nouvelle section

**Implementation technique :**
```python
# Agregation via ORM
Tache.objects.filter(ferme__in=user_fermes, statut='terminee') \
    .values('assigne_a__user__username', 'assigne_a__user__first_name') \
    .annotate(
        terminees=Count('id'),
        a_temps=Count('id', filter=Q(date_terminee__lte=F('date_echeance'))),
        en_retard=Count('id', filter=Q(date_echeance__lt=timezone.now().date(), statut__in=['a_faire','en_cours']))
    )
```

**Mobile :** tableau horizontal scrollable, mini-cartes en grille 1 colonne sous 768px.

---

## 2. Per-Product Predictions in Project Detail

**Approche :** conserver le resume agrege existant, et ajouter le detail par produit.

**Actuellement :** `get_prevision_affichee_projet()` agrege toutes les `PrevisionRecolte` d'un projet en un seul `SimpleNamespace`. Le template `detail_projet.html` affiche ce bloc agrege unique.

**Changement :**
- Dans `detail_projet` (view) : passer non seulement `prediction` (agrege) mais aussi `projet_produits_avec_previsions` — chaque `ProjetProduit` enrichi de sa `PrevisionRecolte` liee (via `pp.prevision` grace au `related_name` OneToOne).
- Dans `detail_projet.html` : dans la section "Produits du projet", ajouter a chaque produit une mini-barre de prediction (rendement min–max, confiance) si une prevision existe.
- Conserver le bloc agrege global existant en haut de la page.

**Fichiers concernes :**
- `baay/views.py` — fonction `detail_projet()` : enrichir `projet_produits` avec leurs previsions
- `templates/projets/detail_projet.html` — ajouter les donnees de prediction dans chaque `.ps-product-item`
- `templates/projets/detail_projet_bento.html` — idem si ce template est actif (verifier quel template est utilise par la vue)

---

## 3. Tests

- `baay/tests.py` — test unitaire pour l'agregation des taches par agent (mock Tache avec differents statuts/echeances)
- Test pour la recuperation des previsions par produit dans le contexte de `detail_projet`

---

## Questions implicites resolues

| Question | Reponse par defaut retenue |
|---|---|
| Metriques productivite | Taches terminees + taux a l'echeance + taches en retard + score composite |
| Scope employes | Ferme filtrable (meme UX que le reste du dashboard) |
| Predictions : remplacer ou complement | Complement — resume global conserve + detail par produit |
