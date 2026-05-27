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
| 3.1 | **Remplacer la messagerie WebSocket par des commentaires** — créer un modèle `Commentaire` générique (FK vers `Ferme`, `ProjetAgricole`, `TacheAgricole` via GenericForeignKey). Remplacer les panels de messagerie par une section commentaires légère (HTMX POST/GET, pas de WebSocket). Désactiver `ChatConsumer` et `InboxConsumer`. | `baay/consumers.py` sans consumers actifs ; modèle `Commentaire` migré ; section commentaires fonctionnelle sur au moins Ferme et TacheAgricole ; aucun appel WebSocket dans le JS. | — | cc:TODO |
| 3.2 | **Onboarding en 3 étapes** — refactoriser le flow post-inscription pour amener un nouvel utilisateur de l'inscription au premier diagnostic lié en ≤ 3 écrans. Étape 1 : créer la ferme. Étape 2 : créer un projet. Étape 3 : lancer un diagnostic BaayVision. Indicateur de progression visible. | Nouveau compte peut atteindre la page de diagnostic liée en 3 clics depuis le mail de confirmation ; barre de progression 1/2/3 visible ; aucune redirection en boucle. | 3.1 | cc:TODO |
| 3.3 | **Dashboard coopérative** — vue spéciale pour le rôle `owner` gérant N fermes : liste des fermes avec dernière prédiction de rendement, dernier diagnostic BaayVision, et statut des tâches critiques. Filtre par ferme. Export CSV. | Dashboard accessible depuis le menu pour un owner multi-fermes ; affiche au moins rendement + dernier diagnostic par ferme ; export CSV fonctionnel. | 3.2 | cc:TODO |
| 3.4 | **Monitoring coût API dans l'admin Django** — créer un modèle `AppelAPILog` (service, timestamp, coût_estimé_usd, cache_hit). Enregistrer chaque appel Gemini. Vue admin avec total quotidien/hebdo, taux de cache hit, et alerte si coût journalier dépasse un seuil configurable. | `AppelAPILog` migré ; chaque appel Gemini crée une entrée ; vue admin affiche coût quotidien et taux de cache hit ; seuil configurable via `settings.py`. | 2.2 | cc:TODO |

---

## Completed

Voir Phase 1 ci-dessus — 8/8 tâches `cc:完了` (2026-05-27).
Phase 2.0 — Page `/diagnostic/` standalone BaayVision : `cc:完了` (2026-05-27).

## Archived

<!-- older completed tasks -->
