# Audit de performance — Andd Baay

> Première passe : 8 mai 2026. Stack : Django 5 + HTMX + Vercel.

## Méthodologie

1. Scan statique du code (greps, lecture des hot-paths).
2. Analyse des bundles statiques (CSS / JS).
3. Setup d'un outil de mesure empirique (`django-debug-toolbar` en dev only).

Pas de mesure synthétique (Lighthouse, WebPageTest) sur cette passe — à faire en suivant.

---

## ✅ Fixes appliqués

### Backend — N+1 dans `dashboard_partial_kpis`

**Symptôme** : la tuile bento "Performance financière" du dashboard exécutait `calculer_kpis_financiers_projet(projet_id)` dans une boucle Python sur tous les projets accessibles. Chaque appel = 5 requêtes SQL (Investissement, Depense, Recette, ProjetProduit, PrevisionRecolte).

**Coût avant** :
- 1 ferme avec 20 projets → ~100 requêtes SQL pour rendre la tuile.
- Comportement quadratique sur les comptes premium multi-fermes.

**Fix** (`baay/services.py` + `baay/views.py`) :
- Nouveau helper `calculer_kpis_financiers_globaux(projet_ids)` qui fait 3 agrégations SQL fixes (`Sum` sur `Investissement`, `Depense`, `Recette` filtrées par `projet_id__in=projet_ids`).
- `dashboard_partial_kpis` remplace la boucle par un seul appel agrégé.

**Coût après** : 4 requêtes (1 pour les IDs + 3 pour les sommes), quel que soit le nombre de projets.

**Gain estimé** : 80-95 % de TTFB sur la tuile KPI. À mesurer avec le toolbar.

---

### Frontend — Script Figma capture en prod

**Symptôme** : `<script src="https://mcp.figma.com/mcp/html-to-design/capture.js" async></script>` chargé sur **toutes** les pages, même en prod, alors qu'il ne sert que pour les captures Figma manuelles ponctuelles.

**Fix** (`templates/base.html`) : commenté. À réactiver localement en décommentant la ligne quand on lance une capture Figma.

**Gain** : -1 requête DNS + -1 requête HTTP par page rendue, économies marginales mais signal cleanup.

---

### Outillage — django-debug-toolbar (dev only)

**Setup** :
- `requirements-dev.txt` : ajout `django-debug-toolbar>=4.4.0`.
- `Andd_Baayi/settings.py` : `DEBUG_TOOLBAR_ENABLED = DEBUG and not IS_VERCEL`. INSTALLED_APPS et MIDDLEWARE conditionnels. Callback désactivant le toolbar pour les requêtes HTMX (sinon il pollue les fragments).
- `Andd_Baayi/urls.py` : route `__debug__/` conditionnelle.

**Garde-fou prod** : si `IS_VERCEL=True` ou `DEBUG=False`, le toolbar n'est jamais chargé. Garanti par le setup conditionnel + le fait que `django-debug-toolbar` n'est pas dans `requirements-vercel.txt`.

**Usage** :

```bash
# Installer en local
pip install -r requirements-dev.txt

# Lancer le serveur en mode debug
python manage.py runserver 8003

# Ouvrir une page qui charge des partials HTMX (ex /dashboard/)
# Le panneau "History" du toolbar montre toutes les requêtes HTMX et leurs SQL.
```

Panneaux à surveiller :
- **SQL** : nombre de requêtes par vue + détail des duplicates (signe de N+1).
- **Profiling** : temps Python par fonction.
- **Cache** : hits/misses du `HtmxCacheMiddleware`.

---

## 🔭 À traiter (par ordre de rentabilité)

### 1. ✅ Externaliser le CSS inline de `base.html` (FAIT)

**Avant** : ~3019 lignes de CSS inline dans `<style>` de `base.html`. Fichier = **148 KB / 4119 lignes**.

**Après** :
- `baay/static/css/base-inline.css` créé (91.8 KB, cacheable navigateur).
- `templates/base.html` réduit à **60.6 KB / 1101 lignes** (−87 KB par page rendue, −3019 lignes).
- `<link rel="stylesheet" href="{% static 'css/base-inline.css' %}">` placé après `mobile-agri-pages.css` et `tailwind_htmx_alpine_head` pour préserver l'ordre de cascade.

**Vérification cascade** : variables `:root`, modes `[data-bs-theme]`, et surcharges sont conservés dans l'ordre original. `manage.py check` OK avec DEBUG=True et DEBUG=False.

**Gain mesuré** : −87 KB de HTML par page rendue. Le CSS extrait est maintenant cacheable côté navigateur (Cache-Control via WhiteNoise) — coût après le premier hit ≈ 0. Sur Vercel CDN : également servi avec long TTL.

**À tester manuellement** : dashboard, finance hub, détail projet, messagerie (vérifier qu'aucun style ne saute).

---

### 2. ✅ Tailwind via CDN runtime → build prod (FAIT)

**Avant** : `<script src="https://cdn.tailwindcss.com"></script>` chargeait **~300 KB de JS** au runtime sur chaque page pour compiler les classes `tw-*` côté navigateur.

**Après** :
- `tailwind.config.js` créé (prefix `tw-`, preflight off, content scanning `templates/**/*.html` + `baay/templates/**/*.html` + `baay/static/js/**/*.js` + `baay/**/*.py`).
- `baay/static/css/_src/tailwind-input.css` (entry point).
- Build local `npm run build:tailwind` → `baay/static/css/tailwind.css` (**6 KB minifié**, purgé sur l'usage réel).
- `templates/includes/tailwind_htmx_alpine_head.html` : remplace le `<script>` CDN par `<link rel="stylesheet" href="{% static 'css/tailwind.css' %}">`.

**Pipeline** : aucun changement Vercel. Le CSS compilé est committé dans le repo (cf. `.gitignore` qui exclut `node_modules/` mais conserve les outputs). Lors d'ajout de nouvelles classes `tw-*`, lancer `npm run build:tailwind` localement avant commit.

**Gain mesuré** : −300 KB JS au runtime + −1 lookup DNS vers `cdn.tailwindcss.com`. Tailwind n'est plus exécuté côté client : pure CSS pré-compilé.

**Mode watch en dev** : `npm run watch:tailwind` régénère à chaque changement.

---

### 3. ✅ Subset Font Awesome (FAIT)

**Avant** : `font-awesome/6.4.0/css/all.min.css` (75 KB) + WOFF2 fonts complets (~140 KB solid + ~120 KB brands) chargés depuis cdnjs.

**Audit usage** : un script PowerShell d'audit grep tous les `fa[srlb]?\s+fa-{name}` dans `templates/`, `baay/static/js/`, `baay/**/*.py`. Résultat : **158 icônes uniques** (155 solid + 3 brands : `instagram`, `linkedin-in`, `twitter`). Liste persistée dans `.fa-icons-used.txt` pour rebuilds reproductibles.

**Après** :
- `scripts/build-fa-subset.mjs` (Node ESM) lit `.fa-icons-used.txt`, partitionne solid/brands, appelle `fontawesome-subset` pour générer les WOFF2 puis produit un CSS minimal en filtrant `node_modules/@fortawesome/fontawesome-free/css/all.css`.
- Outputs committés :
  - `baay/static/css/fa-subset.css` (**15.8 KB** — vs 75 KB CDN).
  - `baay/static/webfonts/fa-solid-900.woff2` (**12.2 KB** — vs ~140 KB CDN).
  - `baay/static/webfonts/fa-brands-400.woff2` (**1 KB** — vs ~120 KB CDN).
- `templates/base.html` : remplace `<link href="https://cdnjs...font-awesome/.../all.min.css">` par `<link href="{% static 'css/fa-subset.css' %}">`.

**Régénérer** : `npm run build:fa` (ou `npm run build:css` pour Tailwind + FA en un coup). Si une nouvelle icône `fa-{name}` est ajoutée dans un template :
1. Régénérer `.fa-icons-used.txt` (script PowerShell d'audit ou ajouter manuellement).
2. `npm run build:fa`.

**Gain mesuré** : **−306 KB sur première visite** (CSS 75→15.8 KB + WOFF2 ~260→13.2 KB). Cache navigateur ensuite ≈ 0.

**Note `fa-sparkles`** : icône Pro-only. Remplacée par `fa-wand-magic-sparkles` (Free, équivalent visuel) dans `templates/home.html` (2 occurrences, lignes 421 et 958).

---

### 4. ✅ Subset Animate.css (FAIT)

**Avant** : `animate.min.css` (~70 KB) chargé entier depuis cdnjs pour 6 animations seulement.

**Audit usage** : grep `animate__\w+` dans `templates/` → 6 classes utilisées :
- `animate__animated` (base, requise)
- `animate__fadeIn`, `animate__fadeInDown`, `animate__fadeInUp`, `animate__fadeInLeft`, `animate__fadeInRight`

**Après** :
- `baay/static/css/animate-subset.css` (≈ 2.2 KB) avec les 6 keyframes copiés depuis animate.css v4.1.1 + bloc `prefers-reduced-motion`.
- CDN cdnjs supprimé de `base.html`.

**Gain mesuré** : −67 KB CSS chargé sur chaque page (et −1 dépendance externe / −1 lookup DNS).

**Note** : si une nouvelle animation `animate__*` est ajoutée dans un template, il faut copier ses `@keyframes` depuis [animate.css source](https://github.com/animate-css/animate.css/blob/main/animate.css). Le commentaire en tête du fichier le rappelle.

---

### 5. Audit des autres views.py (au-delà du dashboard)

`views.py` contient 84 appels `.objects.all/filter/get(...)` et 105 `select_related/prefetch_related`. Le ratio global est sain mais des hotspots sont probables. À auditer en priorité (charges suspectes) :
- Hub finance (`/finance/`) — beaucoup de tables jointes.
- Détail projet (`/projets/<id>/`) — KPIs + recettes + investissements + tâches.
- Liste projets (`/projets/`) — pagination + filtres + agrégats.

Méthode : ouvrir chaque vue avec le toolbar en dev, regarder le panneau SQL, identifier les duplicates.

---

### 6. Cache HTMX fragment — vérifier les hits

Le projet a déjà un `HtmxCacheMiddleware` avec TTL=60s. Mais on a vu que `dashboard/partial/messages/` est exempté (à raison, contenu personnel temps-réel).

À vérifier avec le toolbar :
- Le partial `kpis` est-il bien cache-hit après le 1er chargement d'une session ?
- Le partial `alertes` (jusqu'à ce qu'il soit retiré) avait-il un taux de hit acceptable ?

Si les hit ratios sont faibles, identifier ce qui invalide le cache (vary headers, cookie session…).

---

## 🛠 Prochaines étapes recommandées

1. **Tester manuellement** les pages clés après les actions #1 à #4 :
   - `/` (home, animations + nouvelles `fa-wand-magic-sparkles`).
   - `/dashboard/` (cockpit, bento grid, animations fadeIn, classes `tw-*`).
   - `/finance/` (tableau, filtres, ROI widget).
   - `/projets/<id>/` (détail, cascade animations, FA icônes).
   - `/messagerie/` (drawer, conversation).
   - `/login/` et `/register/` (anims fadeInLeft/Right).
2. **Démarrer le toolbar** : `pip install -r requirements-dev.txt` + restart runserver. Charger `/dashboard/` et regarder le panneau "History" → confirmer que le N+1 KPI est bien résolu (devrait afficher ~4 requêtes pour la tuile).
3. **Mesure baseline LCP** : exécuter Lighthouse sur `/dashboard/` et `/finance/` en dev (via Chrome DevTools Mode mobile, throttling Slow 3G). Comparer avant/après. Cibles : LCP < 2.5s, TBT < 200ms.
4. **Vérifier le DevTools Network tab** sur première visite : aucun appel à `cdn.tailwindcss.com`, `cdnjs.cloudflare.com/.../animate.min.css`, `cdnjs.cloudflare.com/.../font-awesome/...` ou `mcp.figma.com`. Tous les CSS critiques doivent venir de `/static/`.
5. **Audit DB ciblé** : utiliser le toolbar sur `/finance/` et `/projets/<id>/` pour repérer d'autres N+1 (cf. action #5 du plan).

---

## Référentiel

- N+1 fix : `baay/services.py::calculer_kpis_financiers_globaux`, `baay/views.py::dashboard_partial_kpis`.
- Toolbar setup : `Andd_Baayi/settings.py` (bloc `DEBUG_TOOLBAR_ENABLED`), `Andd_Baayi/urls.py` (path `__debug__/`).
- CSS inline extrait : `baay/static/css/base-inline.css` (action #1).
- Tailwind build : `tailwind.config.js`, `baay/static/css/_src/tailwind-input.css`, output `baay/static/css/tailwind.css` (action #2).
- FA subset : `scripts/build-fa-subset.mjs`, `.fa-icons-used.txt`, outputs `baay/static/css/fa-subset.css` + `baay/static/webfonts/fa-{solid-900,brands-400}.woff2` (action #3).
- Animate subset : `baay/static/css/animate-subset.css` (action #4).
- Skill catalogue pertinent : `sentry-django-perf-review` (voir `.cursor/skills/cursor-skills-catalog/SKILL.md`).

## Workflow de build

```bash
# Premier setup
pip install -r requirements-dev.txt   # Django + debug-toolbar
npm install                           # Tailwind + FA subset tooling

# Quand on ajoute des classes tw-* ou des icônes fa-*
npm run build:css                     # = build:tailwind + build:fa

# Pendant le développement (hot reload sur les classes tw-*)
npm run watch:tailwind
```
