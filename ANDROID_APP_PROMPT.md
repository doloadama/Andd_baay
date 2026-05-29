# Prompt — Construction de l'application Android native d'Andd Baay

> **Comment l'utiliser :** copie-colle ce document entier comme premier message à un assistant
> IA (Claude Code, Cursor, Codex, GPT-5, Gemini, etc.) dans un nouveau projet Android Studio
> vide. L'assistant a tout ce qu'il faut pour construire l'application bout-en-bout sans
> reposer de questions de contexte. Les sections sont indépendantes — si tu fais l'implémentation
> par lots, donne-lui les sections 1→6 d'abord (fondations), puis les écrans un par un.

---

## 0. Identité de l'assistant attendue

Tu es un **ingénieur Android senior** spécialisé dans :
- Kotlin moderne (coroutines, Flow, sealed classes, value classes)
- Jetpack Compose Material 3
- Clean Architecture + MVVM + module Gradle multi-module
- Backend Django REST (tu sais lire un `views.py` Django pour comprendre un endpoint)
- Apps **offline-first** pour réseaux 2G/3G instables (zones rurales Afrique de l'Ouest)
- Optimisation pour devices low-end (1-2 Go RAM, Android 8+)
- Internationalisation FR/Wolof avec scripts latins

Tu écris du code **production-ready**, pas de pseudo-code. Tu commentes en français les
règles métier, en anglais le reste. Tu testes ce que tu écris. Tu fournis le code complet
de chaque fichier, jamais de `// reste inchangé` ou `// TODO`.

---

## 1. Contexte produit

### 1.1 Le projet

**Andd Baay** (« Avec Papa » en wolof — référence à l'héritage paysan) est une plateforme
de gestion agricole collaborative conçue pour les exploitations familiales et coopératives
du Sahel (Sénégal, Mali). Elle combine :

- Gestion d'exploitation (fermes, parcelles, projets agricoles, tâches)
- Suivi météo et agroclimat (intégrations ANACIM + Open-Meteo)
- Prévisions de rendement IA (XGBoost entraîné sur données locales)
- Diagnostic phytosanitaire par photo (vision LLM Gemini)
- Suivi des prix de marché (FAO FPMA + OMA Sénégal) avec alertes sur variations
- Actualités agro officielles (ANACIM, Ministère de l'Agriculture, FAO)
- Messagerie temps-réel entre membres d'une exploitation (Django Channels)
- Assistant vocal en wolof (intégration GalsenAI : Whisper + LLaMA + xTTS)

Le backend Django 5.2 est déjà déployé. **Une API REST mobile complète existe déjà sous
`/api/mobile/` et `/api/v1/`** (voir Section 9 pour la liste exhaustive).

Une app Flutter existe (`andd_baay_mobile/`), mais elle est lente sur low-end et difficile
à maintenir. **La présente mission est de construire une nouvelle app Android NATIVE en
Kotlin/Jetpack Compose qui la remplacera.**

### 1.2 Promesse utilisateur

> « En 1 minute par jour, sans connexion stable, je sais ce qui se passe sur ma ferme,
> ce que je dois faire aujourd'hui, combien j'ai vendu et à quel prix mes voisins vendent. »

L'app doit tenir cette promesse **même hors-ligne**.

---

## 2. Public cible et contraintes

### 2.1 Personas

| Persona | Rôle (`MembreFerme.role`) | % users | Spécificités |
|---------|--------------------------|---------|--------------|
| **Bamba**, propriétaire de 5 ha | `owner` | 30 % | Smartphone milieu de gamme, regarde dashboard + alertes prix, valide tâches |
| **Aminata**, manager coop. de 12 fermes | `manager` | 15 % | Tablette ou téléphone récent, change de ferme active souvent |
| **Modou**, technicien agro | `technicien` | 15 % | Diagnostic plante, conseils fertilisation, intervient sur plusieurs fermes |
| **Demba**, ouvrier saisonnier | `ouvrier` | 40 % | Téléphone bas de gamme, illettré ou semi-lettré, **utilise surtout l'audio wolof** |

### 2.2 Contraintes terrain (non-négociables)

- **Android 8.0 (API 26) minimum**, cible API 34 (Android 14). Tester sur émulateur API 26.
- **RAM minimale 1 Go**. Pas d'animations couteuses, listes virtualisées, images compressées.
- **APK final < 25 Mo** (sans bundle vers la Play Store) — code shrinking, R8 fullMode.
- **Hors-ligne complet sur les vues consultation** (dashboard, fermes, projets, tâches,
  prévisions, actualités déjà chargées). Synchro différée pour les écritures.
- **Réseau 2G/3G** : timeout HTTP à 30 s, retry exponentiel avec jitter, compression gzip.
- **Connexion intermittente** : aucune perte de données saisie. File d'attente locale Room
  + WorkManager.
- **Batterie** : pas de polling. Push FCM uniquement. WebSocket fermé si app en background.
- **Stockage** : prévoir purge automatique des données > 30 jours non consultées.
- **Permissions strictes** : pas de localisation en background, pas d'accès contacts.

### 2.3 Langues

- **Français** (primaire) — `values/strings.xml`
- **Wolof script latin** (secondaire) — `values-wo/strings.xml` (code ISO 639-1 manquant
  officiellement, utiliser `wo` ; documenter le fallback dans le README)
- L'app détecte la langue système. L'utilisateur peut forcer la langue dans Paramètres.

---

## 3. Stack technique imposée

### 3.1 Versions (Gradle `libs.versions.toml`)

```toml
[versions]
agp = "8.7.2"
kotlin = "2.0.21"
ksp = "2.0.21-1.0.27"
compose-bom = "2024.11.00"
hilt = "2.52"
hilt-navigation = "1.2.0"
retrofit = "2.11.0"
okhttp = "4.12.0"
moshi = "1.15.1"
room = "2.6.1"
coil = "2.7.0"
work = "2.10.0"
datastore = "1.1.1"
navigation = "2.8.4"
lifecycle = "2.8.7"
camera = "1.4.0"
mlkit-barcode = "17.3.0"
firebase-bom = "33.6.0"
junit = "4.13.2"
turbine = "1.2.0"
mockk = "1.13.13"
```

### 3.2 Libraries (résumé)

| Domaine | Library | Rôle |
|---------|---------|------|
| UI | **Jetpack Compose Material 3** | Toute l'UI |
| Nav | **Navigation Compose** | Routing typed (sealed Routes) |
| DI | **Hilt + KSP** | Injection |
| HTTP | **Retrofit + OkHttp + Moshi** | REST + interceptors |
| WebSocket | **OkHttp WebSocket** | Messagerie temps-réel |
| Local DB | **Room** | Cache offline + queue d'écriture |
| Préfs | **DataStore Preferences** | Token, langue, ferme active |
| Images | **Coil** | Chargement, cache disque |
| Background | **WorkManager + Hilt-Work** | Sync, retry, upload photos |
| Camera | **CameraX** | Diagnostic photo plante |
| Push | **Firebase Messaging** | Alertes prix, messages |
| Crash | **Firebase Crashlytics** | Production monitoring |
| Charts | **YCharts** ou Vico | Graphique évolution prix |
| Audio | **MediaRecorder + ExoPlayer** | Assistant vocal wolof |
| Test | **JUnit4 + Turbine + MockK + Compose UI test** | |

**Interdits** : RxJava, Dagger 2 manuel, LiveData (utiliser StateFlow), AppCompat-only Views.

### 3.3 Modules Gradle

```
:app                         (point d'entrée, navigation racine, thème, DI root)
:core:designsystem           (couleurs, typos, composants atomiques Compose)
:core:ui                     (composants composites : EmptyState, ErrorState, LoadingState)
:core:network                (Retrofit, OkHttp, AuthInterceptor, JwtRefreshAuthenticator)
:core:database               (Room, DAOs, Migrations)
:core:datastore              (DataStore Preferences sealed keys)
:core:domain                 (entités métier purs Kotlin, use cases)
:core:common                 (Result wrapper, extensions, dispatchers)
:core:testing                (test rules, fakes communs)
:feature:auth                (login, register, refresh)
:feature:onboarding          (3 écrans tuto + sélection langue)
:feature:dashboard           (Vue d'ensemble + Baay Simple)
:feature:fermes              (liste, détail, création, switch ferme active)
:feature:projets             (liste, détail, création, produits, avancement)
:feature:taches              (liste assignées, marquer terminée, créer tâche)
:feature:meteo               (météo 7 jours + alertes agroclimat)
:feature:diagnostic          (capture photo + résultat IA)
:feature:previsions          (graphique rendement, comparaison)
:feature:prix                (tableau prix + graphique + alertes)
:feature:actualites          (liste articles + filtres source/catégorie)
:feature:messagerie          (conversations + WebSocket)
:feature:vocal               (assistant vocal wolof)
:feature:profil              (compte, langue, déconnexion)
:sync                        (WorkManager workers de synchro)
```

Chaque `:feature` ne dépend que de `:core:*`. Pas de dépendance feature → feature.

---

## 4. Architecture

### 4.1 Couches

```
┌─────────────────────────────────────────┐
│  UI (Composables + ViewModels)          │  ← :feature:*
├─────────────────────────────────────────┤
│  Domain (UseCases, Entities)            │  ← :core:domain
├─────────────────────────────────────────┤
│  Data (Repositories, DataSources)       │  ← :core:network + :core:database
└─────────────────────────────────────────┘
```

### 4.2 Pattern par feature

```
feature/projets/
├── ProjetsScreen.kt              (Composable racine, collect StateFlow)
├── ProjetsViewModel.kt           (StateFlow<ProjetsUiState>, Hilt)
├── ProjetsUiState.kt             (data class : sealed Loading/Success/Error)
├── components/                   (sous-composables locaux)
├── nav/ProjetsNavigation.kt      (extensions NavGraphBuilder)
└── di/ProjetsModule.kt           (rien si pas de binding spécifique)
```

### 4.3 Result wrapper (`:core:common`)

```kotlin
sealed interface AppResult<out T> {
    data class Success<T>(val data: T) : AppResult<T>
    data class Failure(val error: AppError) : AppResult<Nothing>
    object Loading : AppResult<Nothing>
}

sealed class AppError(open val message: String) {
    object NoNetwork : AppError("Pas de connexion")
    data class Http(val code: Int, override val message: String) : AppError(message)
    data class Validation(val fieldErrors: Map<String, String>) : AppError("Données invalides")
    object Unauthorized : AppError("Session expirée")
    object Timeout : AppError("Délai dépassé")
    data class Unknown(val throwable: Throwable) : AppError(throwable.message ?: "Erreur inconnue")
}
```

### 4.4 Repositories — pattern offline-first

```kotlin
fun observeProjets(fermeId: UUID): Flow<List<Projet>> = flow {
    // 1. Emit cache immediately
    emitAll(dao.observeByFerme(fermeId).map { it.toDomain() })
}.also {
    // 2. Trigger refresh in background
    scope.launch { refreshFromNetwork(fermeId) }
}

suspend fun refreshFromNetwork(fermeId: UUID): AppResult<Unit> = withContext(io) {
    try {
        val response = api.listProjets(fermeId)
        dao.upsertAll(response.results.map { it.toEntity() })
        AppResult.Success(Unit)
    } catch (e: IOException) { AppResult.Failure(AppError.NoNetwork) }
    catch (e: HttpException) { AppResult.Failure(AppError.Http(e.code(), e.message())) }
}
```

**Règle d'or :** l'UI ne distingue jamais cache vs réseau. Elle reçoit un `Flow<List<X>>`
qui se met à jour automatiquement quand le réseau apporte du nouveau.

---

## 5. Design system (`:core:designsystem`)

### 5.1 Couleurs (Material 3)

```kotlin
// Brand
val PrimaryGreen = Color(0xFF1D9E75)        // Vert sahélien — couleur signature
val PrimaryGreenDark = Color(0xFF0D6B52)
val PrimaryGreenLight = Color(0xFF5DCAA5)

// Accent prix/marché
val AccentOchre = Color(0xFFB45309)         // Variations prix critiques
val AccentSand = Color(0xFFE7E8D1)          // Backgrounds chauds

// Sémantique
val SuccessGreen = Color(0xFF16A34A)
val WarningAmber = Color(0xFFD97706)
val CriticalRed = Color(0xFFDC2626)
val InfoBlue = Color(0xFF0369A1)

// Neutres
val Ink = Color(0xFF111827)
val Slate = Color(0xFF374151)
val Mist = Color(0xFF6B7280)
val Cloud = Color(0xFFE5E7EB)
val Snow = Color(0xFFF9FAFB)
```

Builder un `AnddBaayTheme(darkTheme: Boolean = isSystemInDarkTheme())` qui produit
`MaterialTheme(colorScheme = …)` complet. **Dark mode obligatoire** (mode utilisé sous le
soleil sahélien : forte luminosité → utilisateur préfère parfois light, mais en soirée
le dark économise la batterie OLED).

### 5.2 Typographie

- **Headlines** : Inter SemiBold (chargé en font asset, pas Google Fonts en ligne)
- **Body** : Inter Regular
- Tailles : `displayLarge 32sp / titleLarge 22sp / titleMedium 18sp / bodyLarge 16sp /
  bodyMedium 14sp / labelLarge 14sp / labelSmall 12sp`
- **Pas de police custom < 14sp** (lisibilité grand âge / lumière forte)

### 5.3 Composants atomiques à fournir

| Composant | Rôle |
|-----------|------|
| `AbButton(primary/secondary/danger/ghost)` | Boutons standardisés, min-height 48 dp |
| `AbTextField` | Input texte avec label flottant, erreur inline, addon unité (« ha ») |
| `AbCard` | Carte avec ombre légère, ripple |
| `AbChip(filter/status/source)` | Chip filtre cliquable + chip statut coloré |
| `AbBadge(count/dot)` | Pastille de notification |
| `AbSkeleton` | Skeleton loader (rectangle gris animé) |
| `AbEmptyState(icon, title, ctaLabel)` | État vide avec illustration + action |
| `AbErrorState(error, onRetry)` | Erreur réseau / serveur, bouton Réessayer |
| `AbConfirmDialog` | Modal de confirmation (oui/non) avec texte custom |
| `AbBottomSheet` | Bottom sheet Modale standard |
| `AbDatePicker` / `AbDateRangePicker` | Sélecteurs date adaptés FR |
| `AbStatChip(value, label, trend)` | Mini-stat avec flèche tendance |

Tous les composants doivent fonctionner avec `Modifier.semantics` pour TalkBack.

### 5.4 Iconographie

- **Material Symbols** (Outlined par défaut, Filled pour états actifs)
- Pas d'emoji dans l'UI critique (instable selon device) — sauf section actualités/prix
  où ils sont des sources de données

### 5.5 Touch targets

**Tous les éléments cliquables ont min 48×48 dp** (norme Material + Sahel : doigts
souvent en gants ou couverts de terre).

---

## 6. Navigation

### 6.1 Schéma top-level

```
NavHost
├── auth (graph)
│   ├── Login
│   ├── Register
│   ├── ForgotPassword
│   └── EmailVerification
├── onboarding (graph, montré une fois)
│   ├── OnboardingStep1, Step2, Step3
│   └── LanguagePicker
└── main (graph, après login)
    ├── BottomBar { Dashboard, Fermes, Tâches, Messagerie, Profil }
    └── DeepLink graph
        ├── ProjetDetail
        ├── DiagnosticCamera
        ├── PrixMarche
        ├── Actualites
        ├── Vocal
        └── Settings
```

### 6.2 Bottom navigation (5 onglets MAX)

| Icône | Label FR | Label WO | Route |
|-------|----------|----------|-------|
| `dashboard` | Tableau | Dafa | `main/dashboard` |
| `agriculture` | Fermes | Tool | `main/fermes` |
| `task_alt` | Tâches | Liggéey | `main/taches` |
| `forum` | Messages | Mbind | `main/messagerie` |
| `account_circle` | Profil | Bopp | `main/profil` |

**Les autres écrans (météo, diagnostic, prix, actualités, vocal) sont accessibles depuis
le Dashboard via cartes Bento — pas via la bottom bar.**

### 6.3 Routes typées (sealed)

```kotlin
sealed class Route(val path: String) {
    object Login : Route("auth/login")
    object Dashboard : Route("main/dashboard")
    data class FermeDetail(val fermeId: UUID) : Route("main/fermes/$fermeId")
    data class ProjetDetail(val projetId: UUID) : Route("main/projets/$projetId")
    data class DiagnosticResult(val taskId: String) : Route("main/diagnostic/$taskId")
    object PrixMarche : Route("main/prix")
    // ...
    companion object { /* parsers depuis NavBackStackEntry */ }
}
```

---

## 7. Spécifications écrans (détaillées)

> Pour chaque écran : objectif, layout, états (Loading/Empty/Error/Success), interactions,
> appels API, comportement offline, tests à écrire.

### 7.1 Login

**Objectif** : authentifier un utilisateur existant.

**Layout** (Compose) :
- Top : logo Andd Baay (vector) + tagline « Avec Papa, vers de meilleures récoltes »
- Card centrale :
  - `AbTextField` Email/username (autofocus, autocompletion email)
  - `AbTextField` Mot de passe (toggle œil, autocomplete password)
  - `AbButton(primary)` « Se connecter » — disabled tant que champs vides
  - Lien « Mot de passe oublié ? » → `ForgotPassword`
- En bas : « Pas de compte ? S'inscrire » → `Register`
- Optionnel : bouton Google SSO (utilise allauth socialaccount déjà branché backend)

**États** :
- **Loading** : bouton « Se connecter » → spinner inline, champs disabled
- **Error** : Snackbar bas + bordure rouge sur champ incriminé si erreur de validation

**API** :
```
POST /api/token/                  { username, password } → { access, refresh }
POST /api/token/refresh/          { refresh } → { access }
POST /api/mobile/auth/register/   { username, email, password, …profile } → 201
```

**Comportement offline** : refuse de soumettre, affiche un message clair « Pas de
connexion — connecte-toi à internet pour te connecter la première fois ».

**Tokens** : stocker `access` (durée 60 min) en mémoire + `refresh` (durée 7 j) dans
**EncryptedSharedPreferences** (jamais en clair). `JwtRefreshAuthenticator` OkHttp
intercepte les 401 → tente refresh → rejoue requête.

**Tests** :
- ViewModel : login success émet state Success → navigate Dashboard
- ViewModel : login 401 émet error « Email ou mot de passe incorrect »
- Compose : bouton disabled tant que champs vides

### 7.2 Onboarding (premier lancement)

3 cartes swipeables :
1. « Gère ta ferme, tes parcelles, tes tâches »
2. « Reçois prévisions météo et alertes prix »
3. « Diagnostique tes plantes avec une photo »

→ Sélecteur langue (FR/WO) → bouton « Commencer » → `Login`.

Sauvegarder le flag `onboardingDone=true` dans DataStore.

### 7.3 Dashboard (écran central)

**Objectif** : vue d'ensemble en 5 secondes.

**Layout** : `LazyColumn` Bento, organisé en cartes :

```
┌────────────────────────────────────────┐
│  Hero : Bonjour, Bamba — 28 mai 2026   │
│  Ferme active : Ndiaganiao (3 fermes)  │   ← tap → sélecteur
├────────────────────────────────────────┤
│  [Météo aujourd'hui] [Tâches du jour]  │   ← 2 cartes compactes
├────────────────────────────────────────┤
│  ⚠️ Alertes prix (bande, masquée si 0) │   ← chips horizontaux
├────────────────────────────────────────┤
│  Projets en cours (carrousel)          │
├────────────────────────────────────────┤
│  Prédictions de rendement              │   ← cartes culture + tendance
├────────────────────────────────────────┤
│  Actualités récentes (3 articles)      │
├────────────────────────────────────────┤
│  Actions rapides : [📷 Diagnostic] [🎤 Vocal] │
└────────────────────────────────────────┘
```

**Variante Baay Simple** (utilisateur de rôle `ouvrier` uniquement) :
- Affiche UNIQUEMENT « Mes tâches du jour » + gros bouton micro vocal
- Pas d'agrégats financiers, pas de prévisions

**Sélection ferme active** :
- Bottom sheet listant fermes accessibles, indicateur sur ferme active
- Stockée dans DataStore → toutes les autres vues filtrent dessus

**API** (toutes en parallèle via `combine` Flows) :
```
GET /api/mobile/dashboard/?ferme_id=<uuid>       → JSON agrégé
GET /api/mobile/fermes/                          → list fermes
GET /api/mobile/prix/alertes/?jours=7&niveau=warning  → alertes prix
GET /api/mobile/actualites/?page_size=3          → 3 dernières actualités
GET /api/v1/taches/?assignee=me&statut=a_faire   → tâches du jour
```

**Offline** : afficher la dernière version cachée + bandeau gris « Hors-ligne — dernière
mise à jour il y a Xh » (timestamp depuis DataStore).

**Pull-to-refresh** : `SwipeRefresh` qui relance toutes les requêtes.

### 7.4 Fermes — liste

**Layout** : `LazyColumn` de cartes ferme avec :
- Nom + région
- Stats : `N projets`, `M ha`, `K membres`
- Indicateur de ferme active (point vert)
- Tap → `FermeDetail`

**FAB** « + » → écran création ferme (formulaire : nom, latitude/longitude via picker
carte ou GPS bouton, superficie totale, région).

**API** :
```
GET    /api/mobile/fermes/                      → list
POST   /api/mobile/fermes/                      → create
GET    /api/mobile/fermes/<uuid>/               → detail
PATCH  /api/mobile/fermes/<uuid>/               → update
DELETE /api/mobile/fermes/<uuid>/               → delete (owner only)
```

**Permissions** : seuls `owner` et `manager` voient le FAB.

### 7.5 Ferme — détail

**Tabs** :
1. **Vue d'ensemble** : carte mini-map (Google Maps Compose), KPIs, projets actifs
2. **Membres** : liste membres + rôles, bouton « Inviter » (`owner` only)
3. **Historique** : timeline actions récentes (création projets, tâches, intempéries)

### 7.6 Projets

**Liste** (`/projets`) :
- Filtres haut : statut (en_cours / en_pause / clôturé), culture
- Cards de projet : nom, culture (icône), superficie, date semis, statut chip coloré,
  progression % (barre)

**Détail projet** :
- Header : nom, culture, statut, superficie, date semis → date récolte prévue
- Tabs :
  1. **Avancement** : barre + jours depuis semis vs cycle total
  2. **Produits** (`ProjetProduit`) : liste avec rendement prévu, bouton « État végétatif »
     (slider 1-5 étoiles) qui PATCH `etat_vegetatif` et déclenche reprévision IA
  3. **Tâches** : liste des tâches liées au projet
  4. **Coûts** : investissements (intrants, main d'œuvre)

**API** :
```
GET    /api/mobile/fermes/<fermeId>/projets/
GET    /api/mobile/projets/<uuid>/
PATCH  /api/mobile/projets/<uuid>/statut/
GET    /api/mobile/projets/<uuid>/avancement/
GET    /api/mobile/projets/<uuid>/produits/
PATCH  /api/mobile/projet-produits/<ppId>/etat/   { etat_vegetatif: 1..5 }
```

### 7.7 Tâches

**Liste** : groupée par jour (Aujourd'hui, Demain, Cette semaine, Plus tard).
Card tâche : titre, projet associé, échéance, statut, bouton ✓ pour marquer terminée.

**Création** (FAB) : titre, description, projet (dropdown), échéance, assignee.

**API** :
```
GET   /api/v1/taches/?statut=a_faire&assignee=me
POST  /api/v1/taches/                            { titre, description, projet, echeance, assignee }
PATCH /api/v1/taches/<uuid>/statut/              { statut: "terminee" }
```

**Offline** : marquer terminé immédiatement en local + queue Room → WorkManager sync
quand connexion revient. Indicateur « En attente de synchro » sur la carte.

### 7.8 Météo

**Layout** :
- Aujourd'hui : grosse card (température max/min, icône, précipitations, humidité, vent)
- Prochains 6 jours : `LazyRow` de cards compactes
- Alerte agroclimat : bandeau coloré (vert/orange/rouge) si conditions extrêmes
- Conseil agro : court paragraphe contextuel (« Risque de pluie forte demain — protéger
  les jeunes plants »)

**Source** : ce que renvoie déjà le backend Django via `dashboard` ou un nouvel endpoint
dédié si besoin (à demander avant codage). Sinon Open-Meteo direct depuis l'app
(coordonnées de la ferme active).

### 7.9 Diagnostic plante (CameraX + IA)

**Flow** :
1. Écran « Diagnostic plante » → 2 options : « Prendre une photo » / « Choisir dans galerie »
2. CameraX preview pleine page, bouton shutter rond bas centre, flip caméra
3. Après capture → écran de confirmation (preview + champ « Symptômes observés »
   optionnel + bouton « Analyser »)
4. POST async vers backend → écran d'attente avec progression
5. Résultat : maladie identifiée (avec niveau de confiance), traitement recommandé,
   bouton « Sauvegarder dans le projet » (lie au projet/produit)

**API** :
```
POST /api/v1/diagnostic/   multipart: image (jpg), symptomes (text)   → { task_id }
GET  /api/v1/diagnostic/<task_id>/                                    → { status: pending|done|error, result }
```

**Polling** : appel toutes les 3 s pendant max 60 s, puis bascule en notif push (FCM)
quand le résultat arrive.

**Stockage local** : Room table `DiagnosticHistory` (image_uri local, résultat JSON,
date) → consultable hors-ligne.

### 7.10 Prévisions de rendement

**Liste par produit** (chaque `ProjetProduit` actif) :
- Cards : produit, fourchette (min — max kg/ha), confiance %, date récolte prévue
- Tap → graphique évolution prédictions (historique des recalculs depuis semis)
- Section « Comparaison » : tes prévisions vs moyennes régionales

**API** :
```
GET /api/v1/previsions/?projet_produit=<uuid>
```

### 7.11 Prix marchés

**Layout** :
- Bandeau alertes en haut (chips colorés warning/critique)
- Synthèse cartes par produit (mil, sorgho, maïs, etc.) :
  prix moyen, variation 7j, indicateur visuel
- Onglet « Graphique » : ligne Vico avec sélecteur produit + période (7/30/90 j) +
  filtre marché
- Onglet « Tableau » : tous les relevés avec filtre région/marché

**API** :
```
GET /api/mobile/prix/?produit=mil&region=Kaolack&periode=30&page=1&page_size=20
GET /api/mobile/prix/alertes/?niveau=warning&jours=7
```

**Notifications push** : recevoir une notif FCM pour chaque nouvelle alerte critique
(canal `prix_critique`, son par défaut, vibration).

### 7.12 Actualités

**Layout** : `LazyVerticalGrid` de cards article (image + source badge + titre + date).
Filtres haut : `Chip` sources (ANACIM, MAE, FAO…) + catégories.

Tap card → ouvre l'URL originale dans **Chrome Custom Tabs** (pas de WebView interne).

**API** :
```
GET /api/mobile/actualites/?source=anacim&categorie=meteo&page=1&page_size=20
```

### 7.13 Messagerie

**Liste conversations** : avatar + nom + dernier message + badge non lus + timestamp
relatif (« il y a 3 min »).

**Détail conversation** :
- Liste messages (bubbles), pull-to-load-more pour historique
- Composer bas : champ texte multi-ligne + bouton micro (vocal) + bouton envoyer
- En-tête : nom de la ferme/groupe, indicateur « En ligne » si autre user actif

**WebSocket** :
```
wss://<host>/ws/chat/<conversation_id>/?token=<jwt>
```

Schéma payload (déjà défini dans `baay/messaging_contract.py`) :
```json
{
  "type": "message",
  "version": "v1",
  "id": "uuid",
  "auteur": "uuid",
  "auteur_nom": "Bamba",
  "contenu": "...",
  "timestamp": "ISO8601",
  "audio_url": null
}
```

**Comportement app background** : fermer le WebSocket, basculer sur notifs FCM.
À la reprise, réouvrir + `GET /api/messages/?since=<last_ts>` pour rattraper.

### 7.14 Assistant vocal wolof

**Flow** :
1. Bouton micro rond géant centre → appui long pour parler
2. Pendant l'enregistrement : forme d'onde animée + texte « J'écoute… »
3. Relâche → envoi audio au backend (multipart)
4. Backend transcrit (Whisper-wolof) → traduit (wolof→fr) → LLM → traduit (fr→wolof) → TTS
5. Réception : audio TTS joué automatiquement + transcription affichée

**API** :
```
POST /api/v1/assistant-vocal/ multipart: audio (wav/m4a)
→ { transcription_wo, traduction_fr, reponse_fr, reponse_wo, audio_url }
```

Permission `RECORD_AUDIO` demandée juste avant le premier usage.

### 7.15 Profil

Sections :
1. **Compte** : avatar (upload via Cloudinary), nom, téléphone, email (non modifiable)
2. **Préférences** : langue (FR/WO), thème (auto/light/dark), notifications par canal
3. **Données** : « Vider le cache », « Synchroniser maintenant »
4. **Sécurité** : changer mot de passe, sessions actives
5. **À propos** : version app, conditions d'utilisation, politique privée
6. **Déconnexion** (rouge, en bas)

---

## 8. Stratégie offline-first (détaillée)

### 8.1 Stockage local Room

**Tables (entités)** :
```
profile, ferme, projet, projet_produit, tache, prevision_recolte,
prix_marche, alerte_prix, article_actualite, conversation, message,
diagnostic_history, pending_write
```

**`pending_write`** : table générique pour les écritures en attente.

```kotlin
@Entity
data class PendingWrite(
    @PrimaryKey val id: UUID = UUID.randomUUID(),
    val endpoint: String,            // "PATCH /api/v1/taches/.../statut/"
    val method: String,              // "PATCH"
    val payloadJson: String,
    val createdAt: Long = System.currentTimeMillis(),
    val retryCount: Int = 0,
    val lastError: String? = null
)
```

### 8.2 WorkManager — SyncWorker

Un seul `CoroutineWorker` `SyncWorker` :
- Trigger : `PeriodicWorkRequest` toutes les 15 min + `OneTimeWork` après chaque pending_write
- Contraintes : `NetworkType.CONNECTED`
- Backoff : exponentiel, max 5 retry
- Logique :
  1. Lire `pending_write` ordonné par `createdAt`
  2. Pour chacun : rejouer la requête. Si succès → supprimer. Si 4xx définitif (validation) →
     marquer en erreur + notifier user. Si 5xx ou network → retry.
  3. Pull : rafraîchir données critiques (tâches du jour, alertes prix)

### 8.3 Conflits

Stratégie **last-write-wins côté serveur** + horodatage. Pour les tâches : si statut a
changé sur le serveur entre lecture et écriture locale, l'API renvoie 409 → on garde la
version serveur et notifie l'user (« Cette tâche a été modifiée par quelqu'un d'autre »).

### 8.4 Purge cache

WorkManager quotidien :
- Supprime messages > 90 j
- Supprime actualités > 30 j
- Supprime relevés prix > 90 j (mais garde les alertes)
- Compacte la DB (`VACUUM`)

---

## 9. API — référence exhaustive

Base URL prod : `https://andd-baay.onrender.com` (ou `https://andd-baay.vercel.app` selon
le déploiement actif). Tester en dev : `http://10.0.2.2:8000` pour émulateur (= `localhost`
du host).

### 9.1 Authentification

| Méthode | Endpoint | Body | Réponse |
|---------|----------|------|---------|
| POST | `/api/token/` | `{username, password}` | `{access, refresh}` |
| POST | `/api/token/refresh/` | `{refresh}` | `{access}` |
| POST | `/api/mobile/auth/register/` | `{username, email, password, telephone?}` | `201 + user` |
| GET  | `/api/mobile/auth/me/` | — | profil complet |
| PATCH| `/api/mobile/auth/me/` | partial profile | profil mis à jour |

Header : `Authorization: Bearer <access_token>` sur tous les appels protégés.

### 9.2 Géographie

| Méthode | Endpoint | Notes |
|---------|----------|-------|
| GET | `/api/mobile/regions/` | Liste régions Sénégal/Mali |
| GET | `/api/mobile/localites/?region=<id>` | Localités filtrables |

### 9.3 Catalogue

| Méthode | Endpoint | Notes |
|---------|----------|-------|
| GET | `/api/mobile/produits/` | Catalogue produits agricoles |

### 9.4 Fermes

```
GET    /api/mobile/fermes/                        → list paginated
POST   /api/mobile/fermes/                        → create
GET    /api/mobile/fermes/<uuid>/                 → detail
PATCH  /api/mobile/fermes/<uuid>/                 → update
DELETE /api/mobile/fermes/<uuid>/                 → delete (owner)
```

Shape `Ferme` (réponse) :
```json
{
  "id": "uuid",
  "nom": "string",
  "region": "string",
  "localite": { "id": "uuid", "nom": "string" },
  "latitude": 14.69,
  "longitude": -17.44,
  "superficie_totale": 5.0,
  "owner": "uuid",
  "membres_count": 3,
  "projets_count": 12,
  "date_creation": "ISO8601"
}
```

### 9.5 Projets

```
GET   /api/mobile/fermes/<fermeId>/projets/
POST  /api/mobile/fermes/<fermeId>/projets/
GET   /api/mobile/projets/<uuid>/
PATCH /api/mobile/projets/<uuid>/
DELETE /api/mobile/projets/<uuid>/
PATCH /api/mobile/projets/<uuid>/statut/         { statut }
GET   /api/mobile/projets/<uuid>/avancement/
GET   /api/mobile/projets/<uuid>/produits/
POST  /api/mobile/projets/<uuid>/produits/
GET   /api/mobile/projet-produits/<ppId>/
PATCH /api/mobile/projet-produits/<ppId>/
PATCH /api/mobile/projet-produits/<ppId>/etat/   { etat_vegetatif: 1..5 }
```

### 9.6 Tâches

```
GET   /api/v1/taches/?projet=<uuid>&statut=a_faire&assignee=me
POST  /api/v1/taches/
PATCH /api/v1/taches/<uuid>/statut/              { statut }
```

### 9.7 Commentaires

```
GET  /api/v1/commentaires/<ct_label>/<uuid>/
POST /api/v1/commentaires/<ct_label>/<uuid>/     { contenu }
```

### 9.8 Prévisions

```
GET /api/v1/previsions/?projet_produit=<uuid>
```

### 9.9 Diagnostic

```
POST /api/v1/diagnostic/             multipart: image, symptomes?    → { task_id }
GET  /api/v1/diagnostic/<task_id>/                                   → { status, result? }
```

### 9.10 Actualités

```
GET /api/mobile/actualites/?source=<key>&categorie=<key>&page=1&page_size=20
```

### 9.11 Prix marchés

```
GET /api/mobile/prix/?produit=<str>&region=<str>&marche=<str>&periode=30&page=1&page_size=20
GET /api/mobile/prix/alertes/?niveau=warning&produit=<str>&jours=30&page=1
```

### 9.12 Profil

```
GET /api/v1/profile/
```

### 9.13 Dashboard agrégé

```
GET /api/mobile/dashboard/?ferme_id=<uuid>
```

### 9.14 WebSocket

```
wss://<host>/ws/chat/<conversation_id>/?token=<jwt>
wss://<host>/ws/inbox/?token=<jwt>            (notifs nouveau message)
```

### 9.15 Conventions de pagination

Toutes les listes paginées renvoient :
```json
{
  "count": 142,
  "page": 1,
  "page_size": 20,
  "pages": 8,
  "results": [...]
}
```

### 9.16 Codes d'erreur standard

| Code | Sens | Action client |
|------|------|---------------|
| 400 | Validation | Afficher erreurs champ par champ |
| 401 | Non authentifié / expiré | Refresh token, sinon → Login |
| 403 | Pas la permission | Snackbar « Accès refusé pour ce rôle » |
| 404 | Ressource introuvable | Écran 404 ou retour liste |
| 409 | Conflit (concurrence) | Recharger l'objet, dialog d'avertissement |
| 422 | Erreur métier | Message backend tel quel |
| 429 | Rate limit | Backoff exponentiel |
| 5xx | Serveur | Retry + Crashlytics si persistant |

---

## 10. Internationalisation FR / WO

### 10.1 Structure

```
res/values/strings.xml         (FR, défaut)
res/values-wo/strings.xml      (Wolof script latin)
```

### 10.2 Conventions

- **Toutes** les chaînes UI extraites, jamais hardcodées.
- Clés : `feature_screen_element` (ex : `dashboard_greeting_morning`)
- Plurals via `<plurals>` (FR a 2 formes : one/other ; Wolof : 1 forme générale)
- Dates : `DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM).withLocale(Locale("fr","SN"))`
- Nombres : `NumberFormat.getCurrencyInstance(Locale("fr","SN"))` → FCFA via `Currency.getInstance("XOF")`

### 10.3 Exemples (à inclure dès le départ)

```xml
<!-- values/strings.xml -->
<string name="app_name">Andd Baay</string>
<string name="login_title">Connexion</string>
<string name="login_email_label">Email ou nom d\'utilisateur</string>
<string name="login_password_label">Mot de passe</string>
<string name="login_submit">Se connecter</string>
<string name="dashboard_greeting_morning">Bonjour, %1$s</string>
<string name="taches_empty_title">Aucune tâche aujourd\'hui</string>
<string name="prix_unite_fcfa_kg">FCFA/kg</string>
<plurals name="alertes_count">
  <item quantity="one">%d alerte</item>
  <item quantity="other">%d alertes</item>
</plurals>
```

```xml
<!-- values-wo/strings.xml -->
<string name="app_name">Andd Baay</string>
<string name="login_title">Dugg</string>
<string name="login_email_label">Sa mail walla sa tur</string>
<string name="login_password_label">Sa baatu juumtu</string>
<string name="login_submit">Dugg</string>
<string name="dashboard_greeting_morning">Asalaa maalekum, %1$s</string>
<string name="taches_empty_title">Amul liggéey tey</string>
<string name="prix_unite_fcfa_kg">FCFA/kilo</string>
<plurals name="alertes_count">
  <item quantity="other">%d xibaar</item>
</plurals>
```

Faire valider les traductions wolof par un locuteur natif avant publication.

---

## 11. Push notifications (FCM)

### 11.1 Setup

- Ajouter Firebase à l'app, fichier `google-services.json` dans `:app/`
- `FirebaseMessagingService` dans `:app`
- Envoyer le token FCM au backend après login : `POST /api/mobile/fcm-token/` (endpoint à
  créer côté Django — payload `{token, device_id, platform}`)

### 11.2 Canaux de notification (Android 8+)

| Channel ID | Importance | Usage |
|-----------|------------|-------|
| `messages` | HIGH | Nouveau message direct |
| `taches` | DEFAULT | Tâche assignée / rappel échéance |
| `prix_warning` | DEFAULT | Variation prix ≥ 15 % |
| `prix_critique` | HIGH | Variation prix ≥ 30 % |
| `meteo_alerte` | HIGH | Alerte météo extrême |
| `diagnostic` | DEFAULT | Résultat diagnostic disponible |
| `general` | LOW | Annonces produits |

### 11.3 Payload type backend → app

```json
{
  "data": {
    "type": "prix_alerte",
    "alerte_id": "uuid",
    "produit": "mil",
    "variation_pct": "32.5",
    "deep_link": "anddbaay://prix?produit=mil"
  },
  "notification": {
    "title": "Mil ↑ 32% à Kaolack",
    "body": "Variation critique sur 7 jours"
  }
}
```

Toujours utiliser `data` (pas seulement `notification`) pour pouvoir traiter en background.

---

## 12. Permissions Android

```xml
<!-- AndroidManifest.xml -->
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
<uses-permission android:name="android.permission.CAMERA"/>
<uses-permission android:name="android.permission.RECORD_AUDIO"/>
<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>     <!-- Android 13+ -->
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>    <!-- au moment de créer une ferme -->
<uses-feature android:name="android.hardware.camera" android:required="false"/>
```

**Demande runtime** : utiliser `Accompanist Permissions` (ou API native).
**Jamais** demander permission au démarrage : seulement au premier usage de la feature
concernée, avec un écran de pré-explication (« Andd Baay a besoin de la caméra pour
diagnostiquer ta plante. Tu peux refuser, tu pourras toujours utiliser le reste de l'app »).

---

## 13. Sécurité

### 13.1 Stockage tokens

- Refresh token → `EncryptedSharedPreferences` (AES256_GCM, MasterKey AES256)
- Access token → mémoire seule (perdu au kill, refresh automatique au login suivant)

### 13.2 Certificate pinning (production uniquement)

```kotlin
val pinner = CertificatePinner.Builder()
    .add("andd-baay.onrender.com", "sha256/AAAAAAAAAAAAAAAA")
    .build()
OkHttpClient.Builder().certificatePinner(pinner)
```

Récupérer le SHA256 actuel et prévoir une rotation. **Désactiver le pinning en debug**.

### 13.3 Network Security Config

```xml
<!-- network_security_config.xml -->
<network-security-config>
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors><certificates src="system"/></trust-anchors>
    </base-config>
    <debug-overrides>
        <trust-anchors>
            <certificates src="system"/>
            <certificates src="user"/>
        </trust-anchors>
    </debug-overrides>
    <!-- Émulateur dev : autoriser 10.0.2.2 en cleartext -->
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">10.0.2.2</domain>
        <domain includeSubdomains="true">localhost</domain>
    </domain-config>
</network-security-config>
```

### 13.4 ProGuard / R8

`proguard-rules.pro` : conserver les classes Moshi (data classes), Room entities,
Retrofit interfaces, Hilt-générés. Documenter chaque `-keep`.

### 13.5 Autres

- `android:allowBackup="false"` (ne pas backup les tokens via Google)
- `android:fullBackupContent="@xml/backup_rules"` (whitelist : pas de tokens)
- Détection root : avertir en debug uniquement, ne pas bloquer (utilisateur Sahel
  peut avoir téléphone rooté pour des raisons légitimes)
- Pas de logs sensibles en prod : utiliser `Timber` avec arbre `Crashlytics` qui filtre

---

## 14. Performance

### 14.1 Démarrage à froid

- Cible : **< 1.5 s** sur Moto G Play (référence low-end)
- App Startup Library pour initialiser DataStore / Crashlytics
- Pas de `Application.onCreate` qui appelle des SDK lourds en synchrone
- Splash via `androidx.core:core-splashscreen` (pas de Splash Activity dédiée)

### 14.2 Images

- Coil avec disque cache 50 Mo
- Format WebP pour les assets bundlés
- `placeholder` + `error` toujours définis
- Pas de bitmap > 1024 px en mémoire (downsample)

### 14.3 Listes

- `LazyColumn` / `LazyVerticalGrid` toujours avec `key` stable (UUID)
- `contentType` pour le recycling des composables hétérogènes
- Pagination via `androidx.paging:paging-compose` pour listes > 100 items

### 14.4 Compose

- `derivedStateOf` pour les états calculés
- `remember(key)` pour les calculs coûteux
- `Modifier.then(...)` plutôt que conditional chaining
- Stable annotations sur les data classes UI state

### 14.5 Réseau

- HTTP/2 (OkHttp par défaut)
- Compression gzip
- Connection pool 5 connexions, keepalive 5 min
- Cache HTTP 10 Mo (`Cache(cacheDir, 10*1024*1024)`)

### 14.6 Mesure

- **Baseline Profiles** générés via macrobenchmark
- **App Startup Tracing**
- Crashlytics + Firebase Performance

---

## 15. Tests

### 15.1 Pyramide

```
        ▲   E2E (Espresso) — 5 % — happy paths critiques uniquement
       ▲▲   UI Compose — 20 %
      ▲▲▲   Integration (Room + Retrofit MockWebServer) — 25 %
     ▲▲▲▲   Unit (ViewModel, UseCase, mappers) — 50 %
```

### 15.2 Conventions

- Un test par règle métier, pas un test par méthode
- Nommage : `methodOrScenario_expectedBehavior` (ex: `login_when401_emitsCredentialsError`)
- Pas de Thread.sleep — Turbine pour les Flows, IdlingResource pour Espresso
- MockWebServer pour les tests de repository

### 15.3 Couverture cible

- `:core:*` : 80 %
- `:feature:*` (ViewModels) : 70 %
- `:app` : pas obligatoire (intégration manuelle)

### 15.4 Tests obligatoires (à livrer)

- AuthRepository : login success, login 401, refresh token, logout clear tokens
- ProjetsRepository : observe cache-first, refresh updates, offline returns cache
- TacheRepository : marquer terminée offline → pending_write créé, sync rejoue
- SyncWorker : rejoue pending writes, gère 5xx en retry, supprime succès
- PrixViewModel : filtre produit + région applique correctement
- LoginScreen Compose : bouton disabled si champs vides, snackbar erreur visible

---

## 16. Build & distribution

### 16.1 Build types

```
debug         (DEBUG, http://10.0.2.2:8000, pas de pinning)
staging       (RELEASE-like, https://staging.andd-baay.com, pinning relaxed)
release       (RELEASE, https://andd-baay.onrender.com, pinning strict, R8 full, Crashlytics)
```

### 16.2 Build variants flavors

Pas de flavor multi-pays au début. Si Sénégal vs Mali diverge plus tard, ajouter
`productFlavors { senegal, mali }` avec resources géographiques distinctes.

### 16.3 Signature

- Keystore stocké hors repo (`~/.gradle/anddbaay-release.keystore`)
- Variables d'env dans `~/.gradle/gradle.properties`
- **Ne JAMAIS** commiter le keystore ni les passwords

### 16.4 Versioning

- `versionName` : SemVer (`1.0.0`, `1.1.0`, `1.1.1`)
- `versionCode` : entier monotone (`1, 2, 3, ...`) — incrémenter à chaque release Play

### 16.5 CI/CD GitHub Actions

Fichier `.github/workflows/android.yml` à fournir :
- Lint (`./gradlew lintRelease`)
- Test unit (`./gradlew testReleaseUnitTest`)
- Build APK debug pour PR review
- Build AAB signé pour tag `v*.*.*`
- Upload artefacts

### 16.6 Distribution

- Internal track Play Console pour tests bêta
- Closed track pour pilote agriculteurs réels (50 testeurs)
- Production track après 2 semaines de pilote stable

---

## 17. Accessibilité

- TalkBack : tous les éléments interactifs ont `contentDescription` ou `Modifier.semantics`
- Contraste : tester avec Accessibility Scanner (cible WCAG AA — 4.5:1 texte normal)
- Taille texte : respecter `fontScale` jusqu'à 1.5×
- Tap targets : 48×48 dp minimum (Material spec)
- Pas d'info véhiculée par couleur seule : toujours doublée par icône ou texte

---

## 18. Analytics et observabilité

- Firebase Analytics : événements clés uniquement (login, ferme_created, projet_created,
  diagnostic_submit, prix_alerte_clicked, message_sent)
- Crashlytics : crashes + custom keys (userRole, fermeActiveId)
- Pas de tracking comportemental fin (respect RGPD + connectivité limitée)
- Bandeau opt-in analytics au premier lancement (CNIL Sénégal en cours d'évolution,
  mieux vaut anticiper)

---

## 19. Critères d'acceptation par release

### MVP (v1.0.0) — couverture minimale pour ship

- [ ] Login + register fonctionnels avec backend prod
- [ ] Dashboard affiche fermes, projets, météo, 3 actualités
- [ ] Liste fermes + détail + création + sélection ferme active
- [ ] Liste projets + détail + marquer statut + saisir état_vegetatif
- [ ] Liste tâches du jour + marquer terminée (online ET offline)
- [ ] Météo 7 jours
- [ ] Prix marchés : tableau + 1 graphique + alertes
- [ ] Actualités : liste + filtres + ouverture article externe
- [ ] Profil + logout + changement langue FR/WO
- [ ] Push FCM : tâche assignée, alerte prix critique, message
- [ ] Offline : dashboard et listes consultables, écritures queueées
- [ ] APK < 25 Mo, démarrage < 1.5 s sur Moto G Play
- [ ] FR + WO traduits à 100 %, validés par locuteur natif
- [ ] Testé sur Android 8, 10, 13 (3 devices min)

### v1.1 — extensions

- [ ] Messagerie temps-réel WebSocket complète
- [ ] Diagnostic plante par photo
- [ ] Prévisions de rendement avec graphique évolution

### v1.2 — premium

- [ ] Assistant vocal wolof
- [ ] Carte interactive parcelles
- [ ] Export PDF rapport mensuel

---

## 20. Livrables attendus

1. **Repository Git** structuré comme Section 3.3, avec :
   - README complet (setup, run, tests, conventions)
   - CHANGELOG (Keep a Changelog format)
   - Architecture decision records dans `docs/adr/`
2. **APK debug signé** + **AAB release signé** pour le MVP
3. **Documentation API mapping** (Markdown) — pour chaque endpoint, l'écran qui le
   consomme et le DTO Kotlin associé
4. **Captures d'écran** de tous les écrans en FR ET WO, light ET dark, 5.5" ET 6.5"
5. **Vidéo démo 3 min** des flows critiques (login → créer ferme → créer projet →
   marquer tâche → consulter prix)
6. **Rapport de tests** : couverture, screenshots tests UI
7. **Liste connue des dettes techniques** avec impact estimé

---

## 21. Règles de collaboration avec l'IA assistante

Quand tu génères du code :

1. **Toujours le fichier complet**, jamais des bouts ellipsés
2. **Imports en haut**, pas oubliés
3. **Indique le chemin** du fichier en commentaire première ligne :
   `// :feature:projets/src/main/java/com/anddbaay/projets/ProjetsViewModel.kt`
4. **Compile mentalement** avant de livrer — pas d'API inventée
5. **Quand tu hésites entre 2 designs**, demande avant de coder
6. **Quand tu modifies un fichier existant**, montre AVANT/APRÈS en diff unifié
7. **Tests inclus** dès la première version du code, jamais « je rajouterai les tests
   ensuite »
8. **Pas de Stack Overflow copy-paste** : adapte au style de code existant
9. **Commits suggérés** en convention Conventional Commits
   (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`)

---

## 22. Démarrage — première salve

Quand tu reçois ce prompt, commence par :

1. Créer la structure Gradle multi-module (Section 3.3) avec `build.gradle.kts` minimal
   pour chaque module
2. Générer `libs.versions.toml` (Section 3.1)
3. Configurer `:core:designsystem` (couleurs + thème + 3-4 composants atomiques)
4. Configurer `:core:network` (Retrofit + OkHttp + AuthInterceptor + Moshi)
5. Configurer `:core:database` (Room + DAOs vides)
6. Implémenter `:feature:auth` complet (Login + Register + ViewModel + Tests)
7. Implémenter navigation racine (`NavHost` + bottom bar dummy)
8. Vérifier qu'on peut se logger sur le backend dev et naviguer jusqu'au dashboard
   (même vide)

**STOP ici** et présente ton travail. Je validerai avant que tu passes au Dashboard
et à la suite.

---

## 23. Questions à me poser AVANT de coder

Si quelque chose n'est pas clair dans ce prompt, pose la question — ne suppose pas.
Exemples valides :
- « Le backend a-t-il déjà un endpoint pour stocker le token FCM ? »
- « Quelle est l'URL de prod réellement active ? »
- « Le SHA256 du certificat pour le pinning, où le récupérer ? »
- « Existe-t-il une charte graphique avec un logo SVG ? »

Pas valide (tu peux décider toi-même) :
- « Quelle couleur exacte pour les borders ? »
- « Quelle taille de marge entre les cartes ? »

---

**Fin du prompt. À toi de jouer.**
