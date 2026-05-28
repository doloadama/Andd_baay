# Andd Baay Plans.md

Créé: 2026-05-27

---

## Phase 1: README — Amélioration du flux d'onboarding

| Task | Contenu | DoD | Depends | Status |
|------|---------|-----|---------|--------|
| 1.1 | **Réorganiser la structure** — Déplacer "Démarrage rapide" en tête (avant Stack et Architecture). Stack et Architecture passent en section secondaire. | La section "Démarrage rapide" apparaît avant la ligne 20 du README. | — | cc:完了 |
| 1.2 | **Compléter les prérequis** — Mentionner `.python-version` (Python 3.12 fixé par le fichier), ajouter `pip install -r requirements-dev.txt` pour les contributeurs, clarifier Windows vs Linux/Mac activate. | Section Prérequis liste `.python-version`, `requirements-dev.txt`, et les deux commandes activate. | 1.1 | cc:完了 |
| 1.3 | **Ajouter une étape "Vérifier l'installation"** — Après `runserver`, ajouter un bloc de vérification : URL à ouvrir (`http://localhost:8000`), page attendue (formulaire login), et commande de smoke test (`python manage.py check`). | README contient un bloc "Vérifier" avec URL, page attendue, et commande check. | 1.1 | cc:完了 |
| 1.4 | **Ajouter un utilisateur de démo** — Documenter la commande `createsuperuser` avec un exemple de credentials de démo (`admin@example.com / changeme123`) pour que le premier login soit immédiat. | README contient exemple de commande createsuperuser avec credentials exemple clairs. | 1.2 | cc:完了 |
| 1.5 | **Corriger le placeholder clone URL** — Remplacer `<url-du-depot>` par une URL GitHub structurée (`https://github.com/<votre-compte>/andd-baay.git`). | Aucune occurrence de `<url-du-depot>` dans le README. | — | cc:完了 |
| 1.6 | **Unifier la section Tests** — Mentionner `pytest` (fichier `pytest.ini` présent) en plus de `manage.py test`. Ajouter `pytest -v` comme commande recommandée. | Section Tests liste `pytest -v` et `python manage.py test`. | — | cc:完了 |
| 1.7 | **Ajouter la section Mobile (Flutter)** — Documenter l'existence de l'app Flutter (`../andd_baay_mobile`) : stack, prérequis (`flutter` CLI), commande de lancement. | README contient section "Application mobile" avec stack Flutter, commandes et prérequis. | — | cc:完了 |
| 1.8 | **Ajouter une section Dépannage** — Couvrir les erreurs fréquentes au premier démarrage : `.env` manquant, erreur de migration, absence de Redis, avertissements `check --deploy`. | Section Dépannage liste ≥ 3 scénarios d'erreur avec cause et solution. | 1.1, 1.2 | cc:完了 |

---

---

## Phase 2 : Distribution Engine

Objectif : créer une boucle de croissance organique autour de `/diagnostic/` avant d'investir dans la rétention.

| Task | Contenu | DoD | Depends | Status |
|------|---------|-----|---------|--------|
| 2.1 | **WhatsApp share** — ajouter un bouton "Partager sur WhatsApp" sur la page résultats de `/diagnostic/`. Message pré-rempli : nom de la culture + problème principal détecté + lien court vers `/diagnostic/`. | Bouton visible sur la page résultats ; tap ouvre WhatsApp avec message pré-rempli ; fonctionne sur mobile et desktop (wa.me). | — | cc:完了 [aa6a6b0] |
| 2.2 | **Cache Gemini par hash image** — avant tout appel Gemini dans `diagnostic_rapide`, calculer `image_content_hash(image_bytes)` et vérifier un cache Django (clé `bv:{hash}`). En cas de hit, retourner le résultat stocké sans appel API. TTL : 7 jours. | Deux soumissions de la même photo ne déclenchent qu'un seul appel Gemini (vérifié via log ou compteur en test). | — | cc:完了 [aa6a6b0] |
| 2.3 | **Landing pages SEO par culture** — 12 URLs `/diagnostic/<culture>/` (mil, arachide, sorgho…) pré-sélectionnant la culture dans le formulaire. `<title>`, `<meta description>` et `<h1>` uniques par culture. | 12 URLs résolvent ; formulaire pré-sélectionne la bonne culture ; balises SEO uniques ; aucune page 404. | — | cc:完了 [aa6a6b0] |
| 2.4 | **Diagnostic en Wolof** — ajouter un sélecteur `langue` (Français / Wolof) sur le formulaire `/diagnostic/`. Passer `langue` au prompt Gemini pour que les recommandations soient rédigées en Wolof quand sélectionné. | Sélecteur visible ; résultat en Wolof quand sélectionné ; résultat en français par défaut. | 2.2 | cc:完了 [aa6a6b0] |

---

## Phase 3 : Core Tightening

Objectif : supprimer la dette fonctionnelle (WebSocket messaging) et réduire le churn d'onboarding.

| Task | Contenu | DoD | Depends | Status |
|------|---------|-----|---------|--------|
| 3.1 | **Remplacer la messagerie WebSocket par des commentaires** — créer un modèle `Commentaire` générique (FK vers `Ferme`, `ProjetAgricole`, `TacheAgricole` via GenericForeignKey). Remplacer les panels de messagerie par une section commentaires légère (HTMX POST/GET, pas de WebSocket). Désactiver `ChatConsumer` et `InboxConsumer`. | `baay/consumers.py` sans consumers actifs ; modèle `Commentaire` migré ; section commentaires fonctionnelle sur au moins Ferme et TacheAgricole ; aucun appel WebSocket dans le JS. | — | cc:完了 [35522d8] |
| 3.2 | **Onboarding en 3 étapes** — refactoriser le flow post-inscription pour amener un nouvel utilisateur de l'inscription au premier diagnostic lié en ≤ 3 écrans. Étape 1 : créer la ferme. Étape 2 : créer un projet. Étape 3 : lancer un diagnostic BaayVision. Indicateur de progression visible. | Nouveau compte peut atteindre la page de diagnostic liée en 3 clics depuis le mail de confirmation ; barre de progression 1/2/3 visible ; aucune redirection en boucle. | 3.1 | cc:完了 [3b0f1c5] |
| 3.3 | **Dashboard coopérative** — vue spéciale pour le rôle `owner` gérant N fermes : liste des fermes avec dernière prédiction de rendement, dernier diagnostic BaayVision, et statut des tâches critiques. Filtre par ferme. Export CSV. | Dashboard accessible depuis le menu pour un owner multi-fermes ; affiche au moins rendement + dernier diagnostic par ferme ; export CSV fonctionnel. | 3.2 | cc:完了 [9d3be71] |
| 3.4 | **Monitoring coût API dans l'admin Django** — créer un modèle `AppelAPILog` (service, timestamp, coût_estimé_usd, cache_hit). Enregistrer chaque appel Gemini. Vue admin avec total quotidien/hebdo, taux de cache hit, et alerte si coût journalier dépasse un seuil configurable. | `AppelAPILog` migré ; chaque appel Gemini crée une entrée ; vue admin affiche coût quotidien et taux de cache hit ; seuil configurable via `settings.py`. | 2.2 | cc:完了 [2d13822] |

---

---

## Phase 4 : Frontend — Assainissement

Objectif : supprimer la dette CSS (Bootstrap vs Tailwind, namespaces en conflit, 2 598 px en dur) sur le tunnel critique, sans toucher aux écrans périphériques.

| Task | Contenu | DoD | Depends | Status |
|------|---------|-----|---------|--------|
| 4.1 | **Trancher le dilemme CSS** — Retirer l'import Bootstrap des 3 pages critiques (`diagnostic/index.html`, `onboarding/wizard.html`, template coopérative). Remplacer les classes Bootstrap résiduelles par des utilitaires Tailwind équivalents. Bootstrap reste chargé uniquement pour l'admin Django et les écrans secondaires. | Bootstrap non chargé sur ces 3 pages (vérifiable via Network > Coverage) ; UI visuellement identique avant/après ; aucune régression sur les formulaires. | — | cc:完了 [dd3967652] |
| 4.2 | **Créer `tokens.css` central + Stylelint** — Extraire les 6 couleurs de marque, 9 tokens d'espacement, 11 tokens de rayon et 4 ombres dans `baay/static/css/tokens.css` sous namespace `--ab-*`. Configurer `.stylelintrc.json` avec `custom-property-pattern: "^ab-"`. | `tokens.css` existe et est importé dans `base.css` ; `npx stylelint "baay/static/css/tokens.css"` passe sans erreur ; `#1D9E75` n'apparaît qu'une seule fois dans tout le CSS (dans `tokens.css`). | — | cc:完了 [1220762b8] |
| 4.3 | **Migrer les namespaces obsolètes** — Script `scripts/migrate_tokens.py` qui remplace `--fd-`, `--msg-`, `--cockpit-`, `--fh-` par leurs équivalents `--ab-*` déclarés dans `tokens.css`, dans tous les fichiers CSS de `baay/static/css/`. | `grep -r "\-\-fd-\|\-\-msg-\|\-\-cockpit-\|\-\-fh-" baay/static/css/` retourne 0 résultats. | 4.2 | cc:完了 [72622a466] |
| 4.4 | **Purger les `style=` inline sur le tunnel critique** — Supprimer les attributs `style=` dans `templates/diagnostic/index.html`, `templates/onboarding/wizard.html`, `templates/dashboard/cooperative.html`. Remplacer par classes Tailwind ou variables `--ab-*` via classes CSS dédiées. | `grep -c 'style=' templates/diagnostic/index.html templates/onboarding/wizard.html templates/dashboard/cooperative.html` retourne 0 sur chacun. | 4.1, 4.2 | cc:完了 [2c1809474] |

---

## Phase 5 : Terrain & GTM

Objectif : rendre le produit utilisable en conditions réelles (3G, terrain) et décrocher les 50 premiers utilisateurs via une coopérative partenaire.

| Task | Contenu | DoD | Depends | Status |
|------|---------|-----|---------|--------|
| 5.1 | **Pipeline d'analyse asynchrone (Celery + PWA offline)** — Transformer l'appel Gemini synchrone en tâche Celery (`analyze_plant_pest_async`). Ajouter un Service Worker (`baay/static/sw.js`) qui met en file d'attente les soumissions hors ligne et les rejoue à la reconnexion. Afficher un écran intermédiaire "Analyse en cours — vous serez notifié" au lieu de spinner bloquant. | Soumission retourne immédiatement (< 300 ms) avec un ID de tâche ; `celery -A Andd_Baayi worker` traite la tâche et enregistre le résultat ; page résultat se charge sur poll (HTMX `hx-trigger="every 3s"` jusqu'à completion) ; testé avec Chrome DevTools Network throttling "Slow 3G". | — | cc:完了 [6cf13fafc] |
| 5.2 | **Complétion des endpoints REST mobile** — Auditer `baay/serializers_mobile.py` + URLs API : Diagnostic, Tâche, Ferme, Commentaire doivent tous avoir des endpoints REST paginés compatibles Flutter. Ajouter les endpoints manquants. Produire `docs/api_mobile.md` listant tous les endpoints avec méthode, auth, et exemple de payload. | `docs/api_mobile.md` existe avec ≥ 8 endpoints documentés ; test DRF pour chaque endpoint nouveau ; Flutter peut soumettre un diagnostic, créer une tâche et poster un commentaire via l'API. | 5.1 | cc:完了 [ca6feb860] |
| 5.3 | **Flow d'invitation Coopérative (B2B2C)** — Ajouter un système d'invitation : un manager génère un lien `https://<domaine>/rejoindre/<token>/` depuis le dashboard coopératif. Le technicien s'inscrit via ce lien et est automatiquement rattaché à la ferme du manager. Wizard d'onboarding adapté technicien : 2 étapes seulement (profil + première tâche — pas de "créer ferme"). | Manager peut générer et copier un lien d'invitation depuis le dashboard coopératif ; technicien suit le lien, s'inscrit, et apparaît dans la liste membres de la ferme ; wizard technicien n'affiche pas l'étape "Créer ferme". | 3.2, 3.3 | cc:完了 [0302af614] |

---

---

## Phase 6 : Agent Prix & Alertes Marché

Objectif : collecter automatiquement les prix agricoles (FAO FPMA + OMA Sénégal), détecter les variations
significatives (±15 % sur 7 j / ±30 % critique) et les reporter sur l'application web et mobile.

**Sources :** FAO FPMA API (primaire, sans clé, données SEN), OMA Sénégal scraping (fallback).
**Produits cibles :** mil, sorgho, maïs, riz, arachide, niébé, oignon, tomate, patate douce.
**Seuils :** warning ≥ 15 % / 7 j — critique ≥ 30 % / 7 j.

| Task | Contenu | DoD | Depends | Status |
|------|---------|-----|---------|--------|
| 6.1 | **Modèles `PrixMarche` + `AlertePrix` + migrations** — `PrixMarche` : produit_nom, marche_nom, region, prix_unitaire, unite (FCFA/kg), source (fao_fpma \| oma \| autre), date_relevee, source_id. `AlertePrix` : produit_nom, marche_nom, variation_pct, prix_actuel, prix_reference, periode_jours, niveau (info\|warning\|critique), vue (bool). `unique_together` sur (produit, marche, date, source) pour idempotence. | `python manage.py migrate --check` passe ; les deux modèles apparaissent dans l'admin. | — | cc:TODO |
| 6.2 | **Service collecte FAO FPMA API** (`baay/services/prix_service.py`) — `fetch_prix_fao_fpma(pays="SEN")` : GET `https://fpma.fao.org/giews/fpma/rest/data/CommodityPriceData`, timeout 10 s, parse JSON, `update_or_create` sur `source_id=entry["id"]`. Cache Redis 12 h sur la clé `prix_fao_fpma_SEN`. Retourne `(nb_crees, nb_mis_a_jour)`. | Appel manuel retourne ≥ 5 entrées pour le Sénégal sans erreur ; les prix s'affichent dans l'admin. | 6.1 | cc:TODO |
| 6.3 | **Scraper OMA Sénégal** (dans `prix_service.py`) — `fetch_prix_oma()` : GET `http://www.oma.gouv.sn/prix-des-produits.html`, parse tableau HTML (BeautifulSoup), extrait produit / marché / prix / unité. Actif seulement si FAO FPMA retourne < 3 produits sénégalais. | `fetch_prix_oma()` retourne ≥ 1 entrée ou lève `PrixServiceUnavailable` proprement (pas de crash) ; logs INFO tracés. | 6.1 | cc:TODO |
| 6.4 | **Service détection de variations** — `detecter_variations_significatives(periode_jours=7, seuil_warning=15, seuil_critique=30)` : pour chaque couple (produit, marché) ayant ≥ 2 relevés, compare dernier prix vs prix N jours avant via queryset annoté. Crée / met à jour `AlertePrix` en évitant les doublons (même produit × même marché × même jour de détection). | Avec 10 `PrixMarche` injectés en fixture, la fonction crée les `AlertePrix` attendues ; 0 doublon si appelée 2× le même jour. | 6.1 | cc:TODO |
| 6.5 | **Tâches Celery + planification Beat** — `fetch_prix_marche_task` (toutes les 12 h, appelle 6.2 puis 6.3 si besoin) + `detecter_alertes_prix_task` (quotidien 06 h 00, appelle 6.4). Lock Redis pour éviter l'exécution concurrente. Ajout dans `settings.CELERY_BEAT_SCHEDULE`. | Les deux tâches apparaissent dans `celery inspect registered` ; Beat log montre les prochaines exécutions. | 6.2, 6.3, 6.4 | cc:TODO |
| 6.6 | **Page `/marche/prix/`** — Vue `liste_prix` (login_required) : tableau des 7 derniers jours par produit + marché, filtre région / produit / période. Graphique Chart.js (ligne) de l'historique 30 j pour le produit sélectionné. Section "Alertes actives" en haut avec badges rouge/orange. Template `templates/marche/prix.html`. URL `marche/prix/` dans `urls_marche.py`. | Page répond HTTP 200 ; graphique affiché pour au moins 1 produit ; filtres fonctionnels (pas de rechargement complet — HTMX ou JS). | 6.1, 6.4 | cc:TODO |
| 6.7 | **Widget alertes prix sur le dashboard** — Sur `templates/dashboard/index.html` (ou équivalent), ajouter une carte "⚠️ Alertes Prix" listant les 3 dernières `AlertePrix` non vues (niveau ≥ warning) avec badge coloré et lien vers `/marche/prix/`. Marquer comme vues au clic. | Widget visible sur le dashboard pour tout utilisateur authentifié ; clic sur une alerte la marque `vue=True` (HTMX PATCH ou JS fetch). | 6.6 | cc:TODO |
| 6.8 | **Section prix dans la page Actualités** — En tête de `/actualites/`, avant la grille d'articles, afficher un bandeau horizontal "Variations de prix cette semaine" avec les alertes niveau critique/warning de moins de 7 jours, badges colorés, et lien "Voir tous les prix →". Masqué si 0 alertes. | Bandeau visible dans `/actualites/` quand ≥ 1 alerte existe ; absent si 0 alertes (pas d'espace vide). | 6.4 | cc:TODO |
| 6.9 | **Admin Django `PrixMarche` + `AlertePrix`** — `list_display` : produit, marché, prix, unité, source, date_relevee pour PrixMarche ; produit, marché, variation_pct, niveau, vue, date_detection pour AlertePrix. Filtre par source / niveau / région. Action "Marquer comme vues". | Les deux modèles apparaissent dans l'admin Unfold avec filtres fonctionnels. | 6.1 | cc:TODO |
| 6.10 | **API mobile `/api/mobile/prix/`** — Endpoint GET : `?produit=mil&region=Kaolack&periode=30` → liste `PrixMarche` paginée (20/page). Endpoint GET `/api/mobile/prix/alertes/` : alertes actives (niveau ≥ warning, ≤ 30 j), triées par `variation_pct` desc. Serializers dans `serializers_mobile.py`. URLs dans `urls_api_mobile.py`. | Curl sur les deux endpoints retourne JSON valide ; filtre `produit` et `region` fonctionnels ; pagination present. | 6.1, 6.4 | cc:TODO |

---

## Completed

Voir Phase 1 ci-dessus — 8/8 tâches `cc:完了` (2026-05-27).
Phase 2.0 — Page `/diagnostic/` standalone BaayVision : `cc:完了` (2026-05-27).

## Archived

<!-- older completed tasks -->
