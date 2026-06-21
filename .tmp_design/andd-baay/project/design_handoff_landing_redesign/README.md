# Handoff : Refonte de la landing page Andd Baay

## Overview
Refonte complète de la page d'accueil publique d'**Andd Baay** (l'intelligence agricole du Sahel).
L'objectif : passer de la version actuelle — sombre, dense — à une page **claire, aérée et orientée
données ("fintech/AI premium")**, avec un hero beaucoup plus fort, un flux de sections repensé et des
animations riches. La marque (vert / vert profond / or, Space Grotesk + Inter, ton FR + touches Wolof)
est conservée à l'identique.

La cible d'implémentation est le **template Django existant** : `templates/home.html`, rendu par
`baay/views.py → home_view()`, qui étend `templates/base.html`.

---

## About the Design Files
Le fichier `Andd Baay Landing.dc.html` de ce bundle est une **référence de design en HTML** — un prototype
qui montre l'apparence et le comportement visés, **pas du code de production à copier tel quel**.

> ⚠️ Ce `.dc.html` est un "Design Component" qui s'appuie sur un runtime de prototypage (balises
> `<x-dc>`, `<helmet>`, attributs `style-hover`, `ref="{{ setRoot }}"`, classe `Component extends DCLogic`).
> **Rien de tout cela ne doit partir en production.** La tâche est de **recréer ce design dans
> l'environnement existant du codebase** : un template Django (`home.html`) qui étend `base.html`, avec
> du CSS scopé sous `.ab-land` (exactement comme le faisait l'ancienne version) et un petit fichier JS
> vanilla dans `static/js/`.

Concrètement, on remplace le contenu des blocs `{% block extra_css %}` et `{% block content %}` de
`home.html` par la nouvelle structure, et on ajoute un fichier `static/js/landing.js` pour les animations.

---

## Fidelity
**Haute fidélité (hifi).** Couleurs, typographie, espacements, rayons, ombres et interactions sont définitifs
et donnés ci-dessous en valeurs exactes. À reproduire au pixel près en réutilisant les conventions du codebase
(tokens `--ab-*` de `static/css/tokens.css`, Font Awesome déjà chargé, polices déjà importées).

---

## Points d'intégration Django (à respecter)

### Vue & contexte (déjà en place — ne pas casser)
`home_view` (dans `baay/views.py`) fournit au template :

| Variable | Type | Usage dans le design |
|---|---|---|
| `stats.nb_users` | int | Métriques de confiance (optionnel) |
| `stats.nb_projets` | int | Métriques de confiance (optionnel) |
| `stats.nb_localites` | int | Métriques de confiance (optionnel) |
| `stats.show_trust_metrics` | bool | `True` seulement s'il y a une activité réelle |
| `projets_actifs`, `prochain_projet` | — | Présents si `request.user.is_authenticated` |
| `vocal_wolof_audio_enabled` | bool | (context processor) gate des CTA vocaux |
| `request.user.is_authenticated` | bool | Bascule les CTA hero/CTA final |

> La maquette utilise des chiffres de **capacité** ("2 min", "Wolof", "2G", "100 %") plutôt que des compteurs
> d'utilisateurs inventés. **Conserver la logique `{% if stats.show_trust_metrics %}`** de l'ancienne page :
> n'afficher de vrais chiffres (`{{ stats.nb_users|intcomma }}+`, etc.) que lorsqu'ils existent, sinon retomber
> sur les libellés de capacité. Charger `{% load humanize %}` pour `intcomma`.

### Blocs de template à remplir
`home.html` étend `base.html` et redéfinit : `title`, `meta_description`, `og_tags`, `extra_css`, `content`.
Garder les blocs meta/OG existants tels quels.

### URLs Django (remplacer les `href="#"` du prototype)
| Élément du design | URL réelle |
|---|---|
| « Démarrer gratuitement » / « Se connecter » / CTA final | `{% url 'register' %}` |
| « Reprendre mon tableau de bord » (si connecté) | `{% url 'dashboard' %}` |
| « Essayer l'assistant vocal » / « Parler à Jëf Baay » | `{% url 'assistant_vocal' %}` (gated par `vocal_wolof_audio_enabled`) |
| Lien « politique de confidentialité » (FAQ + footer) | `{% url 'confidentialite' %}` |
| Footer « Conditions (CGU) » | `{% url 'cgu' %}` |

Reproduire la bascule auth de l'ancienne page :
```django
{% if request.user.is_authenticated %}
  <a href="{% url 'dashboard' %}" ...>Reprendre mon tableau de bord</a>
  {% if vocal_wolof_audio_enabled %}<a href="{% url 'assistant_vocal' %}" ...>Parler à Jëf Baay</a>{% endif %}
{% else %}
  <a href="{% url 'register' %}" ...>Démarrer gratuitement</a>
  {% if vocal_wolof_audio_enabled %}<a href="{% url 'assistant_vocal' %}" ...>Essayer l'assistant vocal</a>{% endif %}
{% endif %}
```

### Assets (déjà dans le repo)
| Asset | Chemin existant | Usage |
|---|---|---|
| Photo « preuve terrain » | `static/images/hero-farmers.jpg` → `{% static 'images/hero-farmers.jpg' %}` | Fond de la section #preuve |
| Marque (glyphe) | inline SVG (voir design) ou `static/images/anddbaay-mark.svg` | Logo nav + footer |
| Wordmark | `static/images/anddbaay-logo-wordmark.svg` | Optionnel |
| OG cover | `static/images/og-cover.jpg` | Métas (déjà en place) |

Le glyphe de marque est fourni **inline en SVG** dans le design (rect mint + nervure verte + nœuds) pour éviter
une requête ; on peut aussi pointer sur `anddbaay-mark.svg`.

### Polices & icônes
- **Space Grotesk** (titres/chiffres) + **Inter** (corps) — déjà référencées par l'ancienne `home.html`/`base.html`.
  Vérifier qu'elles sont bien importées globalement (sinon `<link>` Google Fonts `Space+Grotesk:400,500,600,700`
  et `Inter:400,500,600,700`).
- **Font Awesome 6** : la maquette utilise les glyphes ci-dessous. Le repo sert un **subset**
  (`static/css/fa-subset.css` + `scripts/build-fa-subset.mjs`). **Ajouter au subset** tout glyphe manquant :
  `seedling, arrow-right, microphone, microphone-lines, wifi, brain, coins, camera-retro, people-group,
  mobile-screen, chart-line, leaf, comments, gear, lock, ellipsis, arrow-trend-up, rotate, cloud-sun-rain,
  bell, mountain-sun, wand-magic-sparkles, route, users, circle-question, plus, user, sitemap, user-doctor,
  seedling, wheat-awn` + brands `facebook-f, x-twitter, whatsapp`.

---

## Structure & sections (de haut en bas)

Tout est scopé sous un conteneur racine `.ab-land` (fond `#F4F8F5`). Largeur de contenu : `max-width: 1200px`
centrée, padding latéral `24px`. Rythme vertical des sections : `padding-top: clamp(64px, 8vw, 108px)`.

1. **Nav (sticky)** — barre translucide (`backdrop-filter: blur(14px)`, fond `rgba(244,248,245,.82)`,
   bordure basse `1px rgba(8,80,65,.08)`). Gauche : glyphe (38px, fond `#E1F5EE`, radius 12) + « Andd Baay » +
   sous-titre « INTELLIGENCE AGRICOLE » (`.66rem`, vert). Centre : liens `Solutions · Jëf Baay · Comment ça
   marche · FAQ`. Droite : « Se connecter » (texte) + bouton « Démarrer » (pilule `#04342C`, blanc).
2. **Hero** (`#accueil`) — grille 2 colonnes `1.02fr 1.06fr`, gap `clamp(28px,4vw,56px)`, alignée centre.
   - Fond clair + 2 halos radiaux flous (vert haut-gauche, or haut-droite) + trame de points en masque radial.
   - Colonne texte : pill eyebrow (fond blanc, point vert pulsé) ; H1 `clamp(2.7rem,5.6vw,4.6rem)` « Faites
     parler / votre **terre.** » avec surlignage en dégradé vert→or sous « terre » ; lead `clamp(1.04,1.35vw,1.2rem)`
     `#46574F` ; 2 CTA (primaire dégradé vert, secondaire blanc bordé) ; rangée de preuve (3 avatars empilés +
     « Installation en 2 min · sans carte bancaire » / « Mode hors-ligne natif inclus »).
   - Colonne mockup : **fenêtre navigateur** (radius 20, ombre portée `0 40px 90px -36px rgba(8,80,65,.42)`) =
     chrome (3 pastilles + barre d'URL `app.anddbaay.sn/tableau-de-bord`) + corps app (rail vert `#04342C` 54px
     d'icônes + panneau `#f7faf8`). Dans le panneau : carte « Rendement prévu » `1,82 t/ha` + badge `+23%` +
     **sparkline SVG animée** ; deux mini-cartes « Prix marché » (barres) et « Météo » (`31°`, pluie 3j, barre).
     **Téléphone flottant** en bas-droite (Jëf Baay + égaliseur animé). Deux **chips flottants** (« +23 % de
     rendement », « Synchronisé hors-ligne ») en `animation: float`.
3. **Marquee de confiance** — bande défilante (`Prédiction IA · Vocal Wolof · Hors-ligne natif · Prix du marché
   · Diagnostic photo · Coopératives · Appli installable`), masque dégradé sur les bords, pause au survol.
4. **Problème** (`#defis`) — eyebrow « Le terrain d'abord », titre « Trois réalités du Sahel, trois réponses
   concrètes », 3 cartes numérotées (01/02/03 en dégradé) : illettrisme → vocal ; réseau → hors-ligne ;
   prix → cours en direct.
5. **Solution / Bento** (`#solution`) — titre centré « Tout ce qu'il faut pour décider, au creux de la main ».
   Grille bento `repeat(3,1fr)`, gap 18 : grande tuile IA (span 2, avec graphe à barres animé) ; tuile vocal ;
   tuile hors-ligne ; tuile prix ; tuile diagnostic ; **tuile coopératives large (span 2, fond sombre
   `#085041→#04342C`)** listant les rôles Propriétaire/Manager/Technicien.
6. **Spotlight Jëf Baay** (`#vocal`) — **moment sombre premium**. Bloc radius 30, fond radial `#0a3a2e→#04241d`,
   halo or, trame de points. Gauche : eyebrow + « L'assistant qui parle votre langue » + CTA or « Essayer
   maintenant ». Droite : bulle de chat (question Wolof utilisateur → réponse bot) + **gros égaliseur animé**.
7. **Étapes** (`#etapes`) — « Opérationnel en 3 étapes », 3 cartes reliées par une ligne pointillée, pastilles
   numérotées (1/2 vert, 3 or).
8. **Preuve terrain** (`#preuve`) — bloc radius 30 avec **photo `hero-farmers.jpg`** en fond + overlay
   dégradé `rgba(4,36,29,…)`. Titre blanc + 4 métriques en dégradé mint→or séparées par filets
   (`2 min` [count-up] · `Wolof` · `2G` · `100 %` [count-up]).
9. **Personas** (`#temoignages`) — « Pensé pour tout l'écosystème agricole », 3 cartes (agriculteur indépendant /
   coopérative / technicien) avec citation en italique + tags pilule.
10. **FAQ** (`#faq`) — 5 `<details>` dans une carte blanche, icône `+` qui pivote à l'ouverture.
11. **CTA final** — bloc radius 32 dégradé vert `#1D9E75→#085041`, halo + trame, « La prochaine saison se
    prépare maintenant. », CTA or + CTA verre.
12. **Footer** — grille 4 colonnes (marque + 3 colonnes de liens), réseaux sociaux, ligne basse
    « © 2026 Andd Baay · Fait au Sénégal » + sélecteur de langue Français/English/Wolof.

---

## Design Tokens (valeurs exactes)

> La plupart existent déjà dans `static/css/tokens.css` (`--ab-color-*`). Réutiliser ces variables ;
> les valeurs brutes ci-dessous ne sont là que pour référence.

### Couleurs
| Rôle | Hex | Token existant |
|---|---|---|
| Fond page | `#F4F8F5` | — (clair, dérivé) |
| Vert primaire | `#1D9E75` | `--ab-color-primary` |
| Vert profond | `#085041` | `--ab-color-primary-deep` |
| Vert nuit (sections sombres) | `#04342C` / `#04241d` | `--ab-color-primary-night` |
| Vert clair / mint | `#5DCAA5` · `#9FE1CB` · `#E1F5EE` · `#E8F8F1` | — |
| Or (accent) | `#EF9F27` | `--ab-color-accent` |
| Or foncé (CTA texte) | `#3a2400` | — |
| Encre titres | `#0B2620` | (≈ `--ab-color-text`) |
| Texte courant | `#46574F` / `#51635B` | — |
| Texte atténué | `#6a7a72` / `#86968f` | `--ab-color-text-muted` |
| Filet / bordure | `rgba(8,80,65,.10)` | — |
| Surface carte | `#ffffff` | `--ab-color-surface` |

### Typographie
- Display / titres / chiffres : **Space Grotesk** (`--ab-font-display`), `letter-spacing: -.03em`, `line-height: 1.05`, poids 600–700.
- Corps : **Inter** (`--ab-font-sans`), `line-height: 1.6`.
- Échelle clés : H1 `clamp(2.7rem,5.6vw,4.6rem)` · H2 `clamp(2rem,3.7vw,3rem)` · titres cartes `1.14–1.2rem` ·
  lead `clamp(1.04rem,1.35vw,1.2rem)` · corps carte `.95rem` · eyebrow `.8rem/600`.

### Rayons / ombres / espacements
- Rayons : cartes `20–22px` · gros blocs `30–32px` · pills `999px` · icônes `15–16px`.
- Ombre carte au survol : `0 26px 50px -26px rgba(8,80,65,.4)`.
- Ombre mockup hero : `0 40px 90px -36px rgba(8,80,65,.42)`.
- Gap grilles : `18px` (cartes), `22px` (étapes/preuve). Padding cartes : `28px`. Padding sections : `clamp(64px,8vw,108px)` haut.

### Dégradés réutilisés
- Bouton primaire : `linear-gradient(135deg,#1D9E75,#085041)`.
- Surlignage hero + chiffres preuve : `linear-gradient(90deg,#1D9E75,#EF9F27)` / `linear-gradient(100deg,#9FE1CB,#EF9F27)`.
- CTA final : `linear-gradient(135deg,#1D9E75,#085041 72%)`.

---

## Interactions & Behavior

À implémenter en **JS vanilla** (`static/js/landing.js`, chargé en bas du `{% block content %}` ou via
`{% block extra_js %}`). Le prototype le fait via une classe runtime ; voici l'équivalent autonome.

### 1. Révélation au scroll
Tout élément `[data-rv]` part masqué et apparaît quand il entre dans le viewport. `data-rv="<ms>"` = délai
de stagger. **Dégrader proprement** : si JS absent, tout reste visible (ne masquer que via JS).

```js
// static/js/landing.js
(function () {
  var root = document.querySelector('.ab-land');
  if (!root) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return; // respecter l'accessibilité

  var items = Array.prototype.slice.call(root.querySelectorAll('[data-rv]'));
  items.forEach(function (el) {
    el.style.opacity = '0';
    el.style.transform = 'translateY(28px)';
    el.style.transition = 'opacity .8s cubic-bezier(.2,.8,.2,1), transform .8s cubic-bezier(.2,.8,.2,1)';
    var d = el.getAttribute('data-rv');
    if (d) el.style.transitionDelay = d + 'ms';
  });

  function reveal(el) {
    if (el.__shown) return;
    el.__shown = true;
    el.style.opacity = '1';
    el.style.transform = 'none';
    el.querySelectorAll('[data-count]').forEach(animateCount);
    if (el.hasAttribute('data-count')) animateCount(el);
  }

  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { reveal(e.target); io.unobserve(e.target); } });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
    items.forEach(function (el) { io.observe(el); });
  } else {
    items.forEach(reveal); // pas d'IO → tout visible
  }

  // 2. Compteurs animés ([data-count] avec data-dec, data-suffix)
  function animateCount(el) {
    if (el.__counted) return; el.__counted = true;
    var target = parseFloat(el.getAttribute('data-count'));
    var dec = parseInt(el.getAttribute('data-dec') || '0', 10);
    var suffix = el.getAttribute('data-suffix') || '';
    var dur = 1500, start = performance.now();
    function fmt(v) {
      var s = v.toFixed(dec).split('.');
      s[0] = s[0].replace(/\B(?=(\d{3})+(?!\d))/g, '\u202f'); // séparateur milliers
      return s.join(',');
    }
    (function tick(now) {
      var p = Math.min(1, (now - start) / dur);
      var e = 1 - Math.pow(1 - p, 3); // easeOutCubic
      el.textContent = fmt(target * e) + suffix;
      if (p < 1) requestAnimationFrame(tick);
    })(start);
  }
})();
```

### 2. Animations CSS (déclaratives, dans le `<style>` scopé)
Reprendre les `@keyframes` du prototype :
- `pulse` (points verts EN DIRECT) · `aurora` (halos hero) · `fill` (sparkline SVG `stroke-dashoffset`) ·
  `grow` (barres de graphe, `transform: scaleY`) · `eq` (barres d'égaliseur) · `scroll` (marquee, `translateX(-50%)`) ·
  `float` (chips hero) · `draw` (tracé sparkline).
- La sparkline SVG : `stroke-dasharray: 320; stroke-dashoffset: 320; animation: draw 1.8s … forwards`.

### 3. États de survol
- **Cartes** (`.ab-card`, défis, personas, tuiles bento) : `transform: translateY(-4/-5px)`, bordure → `#9FE1CB`,
  ombre `0 26px 50px -26px rgba(8,80,65,.4)`. Transition `.35s cubic-bezier(.2,.8,.2,1)`.
- **Boutons** : `translateY(-3px)` + ombre renforcée.
- **Liens nav / footer** : couleur → `#1D9E75`.
- **Réseaux sociaux footer** : fond `#E8F8F1`→`#1D9E75`, icône → blanc.

### 4. FAQ
`<details>/<summary>`, `summary { list-style:none }`, masquer le marqueur ; icône `.fa-plus` qui passe en
`rotate(45deg)` quand `details[open]`.

### 5. Responsive
- `≤ 991px` : hero en 1 colonne ; grilles 3-cols → 2-cols ; bento spans réduits ; étapes en 1 colonne (masquer
  la ligne pointillée) ; spotlight en 1 colonne.
- `≤ 575px` : toutes les grilles en 1 colonne ; chips flottants `display:none` ; preuve en 1 colonne (filets →
  bordures hautes) ; CTA pleine largeur.
- `prefers-reduced-motion: reduce` : couper toutes les animations + révéler sans transition.

### 6. Dark mode (optionnel)
L'ancienne page gérait `html.dark-mode .ab-land`. Si le toggle de thème global existe encore, prévoir les
surcharges (encre claire, surfaces `#0a2f26`, filets `rgba(159,225,203,.16)`). Sinon, ignorer.

---

## Accessibilité
- Éléments purement décoratifs (mockup, chips, égaliseurs, halos) : `aria-hidden="true"`.
- Phrases Wolof : `lang="wo"`.
- Contraste : texte `#0B2620` sur `#F4F8F5` OK ; sur sections sombres, texte ≥ `#bfe9da`.
- Cibles tactiles ≥ 44px ; focus visible sur boutons/CTA (anciennement `box-shadow: 0 0 0 2px #fff, 0 0 0 4px primary`).

---

## Files
- `Andd Baay Landing.dc.html` — **la référence de design** (prototype). Ouvrir dans un navigateur pour voir le
  rendu + les animations. Le markup et les styles inline sont à transposer dans `home.html` (CSS scopé `.ab-land`)
  + `static/js/landing.js`.
- `assets/hero-farmers.jpg` — déjà présent dans le repo sous `static/images/hero-farmers.jpg`.
- `assets/anddbaay-logo-wordmark.svg` — déjà présent sous `static/images/`.

### Fichiers du codebase à modifier
- `templates/home.html` — remplacer `{% block extra_css %}` (CSS scopé `.ab-land`) et `{% block content %}` (nouvelle structure). Garder les blocs `title` / `meta_description` / `og_tags`.
- `static/js/landing.js` — **nouveau** (script ci-dessus). Le charger depuis `home.html`.
- `static/css/fa-subset.css` (+ `scripts/build-fa-subset.mjs`) — ajouter les glyphes FA manquants listés plus haut.
- `static/css/tokens.css` — aucune modif nécessaire ; réutiliser les `--ab-*`.

---

## Recommandation d'implémentation
Suivre exactement le modèle de l'ancienne `home.html` : un seul `{% block content %}` contenant
`<div class="ab-land"> … </div>`, et **tout le CSS dans `{% block extra_css %}` scopé sous `.ab-land`**
(convertir les styles inline du prototype en règles `.ab-*` comme le faisait déjà l'ancienne page — c'est plus
maintenable que des styles inline). Les valeurs (couleurs, rayons, type) sont identiques à celles documentées
ici. Brancher les `{% url %}`, la bascule `is_authenticated` et la condition `show_trust_metrics`, puis ajouter
`landing.js`. Tester hors-ligne / 2G (la page reste légère : tout est CSS/SVG sauf une photo).
