---
name: Andd Baay
colors:
  brand:
    primary: "#1D9E75"
    deep: "#085041"
    night: "#04342C"
    pale: "#9FE1CB"
    light: "#5DCAA5"
    bg: "#E1F5EE"
    accent: "#EF9F27"
  functional:
    danger: "#ef4444"
    success: "#1D9E75"
    info: "#3b82f6"
    warning: "#EF9F27"
  light:
    bgDeep: "#E1F5EE"
    bgSecondary: "#f4fbf8"
    bgTertiary: "#d8efe6"
    cardGlass: "rgba(255,255,255,0.92)"
    cardSolid: "#ffffff"
    textMain: "#2C2C2A"
    textSecondary: "#454542"
    textMuted: "#5c5c57"
    textInverse: "#ffffff"
    borderGlass: "rgba(8,80,65,0.1)"
    glassBg: "rgba(255,255,255,0.88)"
  dark:
    bgDeep: "#0a0f0e"
    bgSecondary: "#121c19"
    bgTertiary: "#1a2924"
    cardGlass: "rgba(18,28,25,0.85)"
    cardSolid: "#121c19"
    textMain: "#E8F5F0"
    textSecondary: "#c4d9d0"
    textMuted: "#8aa89e"
    textInverse: "#ffffff"
    borderGlass: "rgba(93,202,165,0.12)"
    glassBg: "rgba(18,28,25,0.78)"
  subtle:
    danger: "rgba(239,68,68,0.12)"
    success: "rgba(29,158,117,0.12)"
    warning: "rgba(239,159,39,0.14)"
    info: "rgba(59,130,246,0.12)"
    accent: "rgba(29,158,117,0.14)"
typography:
  body:
    fontFamily: "'Inter', sans-serif"
    weights: [400, 500, 600, 700]
  display:
    fontFamily: "'Space Grotesk', sans-serif"
    weights: [400, 500, 600, 700, 800]
  scale:
    pageTitle: { fontSize: "1.75rem", fontWeight: 800, letterSpacing: "-0.02em" }
    sectionTitle: { fontSize: "1.125rem", fontWeight: 700 }
    body: { fontSize: "0.9375rem", fontWeight: 400 }
    small: { fontSize: "0.85rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }
    badge: { fontSize: "0.75rem", fontWeight: 800, textTransform: "uppercase" }
spacing:
  scale:
    - { token: "space-1", value: "4px" }
    - { token: "space-2", value: "8px" }
    - { token: "space-3", value: "12px" }
    - { token: "space-4", value: "16px" }
    - { token: "space-5", value: "20px" }
    - { token: "space-6", value: "24px" }
    - { token: "space-7", value: "28px" }
    - { token: "space-8", value: "32px" }
    - { token: "space-10", value: "40px" }
radii:
  xs: "6px"
  sm: "10px"
  input: "12px"
  tight: "14px"
  md: "16px"
  lgUi: "18px"
  card: "22px"
  xl: "28px"
  panel: "32px"
  pill: "40px"
shadows:
  sm: "0 2px 8px rgba(8,80,65,0.06)"
  md: "0 4px 16px rgba(8,80,65,0.08)"
  lg: "0 12px 32px rgba(8,80,65,0.12)"
  glow: "0 10px 30px rgba(29,158,117,0.12)"
  dark:
    sm: "0 2px 8px rgba(0,0,0,0.2)"
    md: "0 4px 16px rgba(0,0,0,0.3)"
    lg: "0 12px 32px rgba(0,0,0,0.4)"
    glow: "0 10px 40px rgba(0,0,0,0.4)"
transitions:
  standard: "0.3s cubic-bezier(0.4, 0, 0.2, 1)"
  fast: "0.15s cubic-bezier(0.4, 0, 0.2, 1)"
components:
  buttonPrimary:
    background: "linear-gradient(135deg, var(--brand-primary), var(--brand-deep))"
    color: "#ffffff"
    borderRadius: "var(--radius-tight)"
    boxShadow: "0 4px 15px rgba(29,158,117,0.25)"
  buttonSecondary:
    background: "linear-gradient(135deg, var(--brand-accent), #d98a1c)"
    color: "#ffffff"
    borderRadius: "var(--radius-tight)"
  buttonOutline:
    background: "transparent"
    border: "2px solid var(--border-glass)"
    color: "var(--text-main)"
    borderRadius: "var(--radius-tight)"
  buttonGhost:
    background: "transparent"
    color: "var(--text-muted)"
    borderRadius: "var(--radius-tight)"
  glassCard:
    background: "var(--glass-bg)"
    backdropFilter: "blur(14px)"
    border: "1px solid var(--border-glass)"
    borderRadius: "var(--radius-card)"
    boxShadow: "var(--shadow-glow)"
  statusBadge:
    enCours:
      background: "rgba(29,158,117,0.1)"
      color: "var(--brand-primary)"
      border: "1px solid var(--brand-primary)"
    enPause:
      background: "rgba(239,159,39,0.1)"
      color: "var(--terroir-ocre)"
      border: "1px solid var(--terroir-ocre)"
    fini:
      background: "rgba(255,215,0,0.1)"
      color: "var(--sun-yellow)"
      border: "1px solid var(--sun-yellow)"
    cloture:
      background: "#95a5a6"
      color: "#ffffff"
  hero:
    background: "linear-gradient(135deg, var(--brand-night) 0%, var(--brand-deep) 44%, var(--brand-primary) 100%)"
    borderRadius: "clamp(14px, 2.5vw, 20px)"
    pattern: "radial-gradient(circle, rgba(255,255,255,0.35) 1px, transparent 1px)"
    patternSize: "22px"
    patternOpacity: 0.35
  weatherWidget:
    pill:
      background: "rgba(255,255,255,0.10)"
      border: "1px solid rgba(255,255,255,0.14)"
      backdropFilter: "blur(10px)"
      borderRadius: "50px"
    themes:
      clearDay: { panelClass: "pd-meteo--clear-day", icon: "fa-sun", color: "#f59e0b" }
      cloudy: { panelClass: "pd-meteo--cloudy", icon: "fa-cloud", color: "#9ca3af" }
      rain: { panelClass: "pd-meteo--rain", icon: "fa-cloud-rain", color: "#3b82f6" }
      storm: { panelClass: "pd-meteo--storm", icon: "fa-bolt", color: "#6366f1" }
  mapWidget:
    container:
      height: "280px"
      borderRadius: "var(--radius-sm)"
      border: "1px solid var(--border-glass)"
    sourceBadge:
      background: "rgba(255,255,255,0.92)"
      borderRadius: "999px"
      fontSize: "11px"
      fontWeight: 700
  localisationCard:
    layout: "grid"
    columns: "minmax(220px, 0.9fr) minmax(260px, 1.2fr)"
    gap: "16px"
    panel:
      background: "radial-gradient(circle at top left, rgba(93,202,165,0.12), transparent 45%), var(--ps-bg)"
      border: "1px solid var(--border-glass)"
      borderRadius: "var(--radius-sm)"
breakpoints:
  xs: "360px"
  sm: "480px"
  md: "768px"
  lg: "991.98px"
  xl: "1024px"
---

# Andd Baay — Design System

> **Premium Afro-Tech** aesthetic — a modern agricultural platform blending West African warmth with clean tech interfaces. Machine-readable tokens live in the YAML front matter above; human-readable rationale follows below.

---

## Overview

**Architectural Minimalism meets Sahelian Warmth.** The UI evokes a premium matte finish — a high-end agricultural dashboard with cultural texture. Every surface uses glass morphism, generous rounding, and a signature green gradient language that signals both environmental stewardship and technical advancement.

**Brand Name:** Andd Baay (Wolof: *"cultivate well"*)
**Tagline:** L'agriculture de demain
**Personality:** Professional, warm, trustworthy, technically advanced
**Audience:** Sahelian farmers & agricultural cooperatives (Senegal focus)
**Languages:** French (primary), English

---

## Color Philosophy

The palette is rooted in high-contrast neutrals and a green accent family that references the Sahelian landscape.

- **Primary (#1D9E75):** Deep emerald — the signature brand color for actions, links, and positive states. Evokes fertile land and growth.
- **Deep (#085041):** Forest green — gradient endpoints, hover states, depth.
- **Night (#04342C):** Near-black green — hero backgrounds, dark mode anchors.
- **Light (#5DCAA5):** Mint — dark-mode accent, hover highlights.
- **Accent (#EF9F27):** Safran/ochre — CTAs, warnings, harvest warmth. The sole warm counterpoint to the green family.
- **Pale (#9FE1CB):** Subtle highlights, tags, decorative elements.

Status colors are chosen for WCAG AA contrast against both light and dark backgrounds.

---

## Typography

**Inter** handles all body text — it's optimized for screen readability at small sizes and supports extended Latin for French diacritics.

**Space Grotesk** handles display text — headings, buttons, page titles. Its geometric construction feels modern and technical without being cold.

The scale is tight and purposeful: large page titles (1.75rem/800wt) for impact, small uppercase labels (0.75rem/800wt) for metadata and badges. This creates clear hierarchy without excessive size variation.

---

## Spacing Philosophy

Layouts are generous and breathable. Cards use 28px internal padding. Grid gaps are 16px minimum. The hero uses `clamp(16px, 4vw, 28px)` to scale gracefully across devices.

This generosity signals quality — the interface never feels cramped, even on mobile.

---

## Border Radii Philosophy

Every surface is rounded. Cards at 22px, pills at 40px, inputs at 12px. This creates a friendly, approachable feel that contrasts with the technical depth of the data.

Bootstrap 5 components are fully overridden to match this language — no sharp corners remain in the default component library.

---

## Shadow & Elevation

Shadows are subtle and green-tinted in light mode (`rgba(8,80,65,0.06-0.12)`), switching to pure black in dark mode. The glow shadow (`--shadow-glow`) is reserved for glass cards and hero elements — it creates a halo effect that lifts premium surfaces.

---

## Component Rationale

### Buttons

Primary buttons use a 135° green gradient with a glow shadow. On hover they lift (`translateY(-3px)`) and the glow intensifies. This creates a tactile, physical feel.

Secondary buttons use the saffron/ochre gradient — reserved for alternative actions and warnings.

Outline and ghost variants provide hierarchy without visual weight.

### Glass Cards

`.glass-card` is the signature surface. It uses `backdrop-filter: blur(14px)` with a semi-transparent white/green background and a subtle border. This creates depth without opacity issues — content behind remains readable but recedes.

### Status Badges

Each project status has a dedicated color treatment:
- **En cours** — green with subtle neon pulse animation (respects `prefers-reduced-motion`)
- **En pause** — saffron/ochre
- **Fini** — gold/yellow
- **Clôturé** — neutral gray

### Hero

The hero uses a three-stop gradient from night → deep → primary, with a white dot-grid pattern overlay (22px spacing, 35% opacity) for texture. A radial glow at top-right adds dimensional light. Status pills and weather widgets float above with glass morphism.

### Weather Widget

Dynamic themes based on OpenWeatherMap icon codes. Each theme maps to a CSS class, FontAwesome icon, and color palette. The pill uses glass morphism with a 50px border radius.

### Localisation Widget

Two-column layout: info panel on the left with coordinate metrics and action buttons, map on the right. The map shows a source badge (GPS ferme / Localité / Approximation) and zooms closer for precise GPS coordinates.

---

## Dark Mode Strategy

Dark mode is not an afterthought — both themes are first-class.

Activation happens via `html.dark-mode` class, set by an anti-flash script in `<head>` that reads `localStorage('theme')` before any CSS renders. This prevents FOUC.

The token system handles everything automatically:
- Backgrounds shift to deep blacks/greens
- Text inverts to light greens/whites
- Borders become subtle green glows
- Shadows switch to pure black
- Accent shifts from primary → light

No component explicitly checks dark mode.

---

## Mobile Strategy

**Mobile-first, progressive enhancement.**

- Bottom navigation sheet replaces desktop sidebar
- Touch targets minimum 44×44px
- Horizontal scrolling for stat cards and farm cards with `scroll-snap-type`
- Safe area insets for bottom sheets
- No hover-only interactions — all hover effects have touch fallbacks

Breakpoints: 360px / 480px / 768px / 991.98px / 1024px

---

## Accessibility

| Principle | Implementation |
|-----------|---------------|
| **Skip link** | `.skip-link` → `#main`, visible on focus |
| **Focus visible** | `3px solid rgba(29,158,117,0.5)` with 3px offset |
| **ARIA** | `aria-label`, `aria-expanded`, `role="menu"`, `aria-current="page"` throughout nav |
| **Touch targets** | `min-height: 44px` on all interactive elements |
| **Color contrast** | Status colors chosen for WCAG AA against both themes |
| **Reduced motion** | Neon pulse and shimmer animations gated behind `prefers-reduced-motion: no-preference` |
| **Screen reader** | `aria-hidden="true"` on decorative icons |
| **Offline status** | `role="status"` + `aria-live="polite"` on offline badge |

---

## Performance

| Optimization | Savings |
|-------------|---------|
| Font Awesome subset (159 icons) | ~306 KB |
| Animate.css subset (6 animations) | ~65 KB |
| Bootstrap CSS vendored locally | No CDN RTT |
| Chart.js lazy-loaded | Deferred ~200 KB |
| Tailwind built with purge | Minimal CSS |
| `backdrop-filter` used sparingly | GPU-friendly |

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Framework | Django Templates | Server-rendered HTML |
| CSS Base | Bootstrap 5.3.0 (local) | Grid, utilities, modal, dropdown |
| CSS Custom | Hand-written CSS | All design tokens + components |
| Tailwind | v3 (`tw-` prefix) | Utility classes, preflight disabled |
| JS | Vanilla JS + Alpine.js | Dropdowns, drawers, offline sync |
| HTMX | Loaded in head | Progressive enhancement |
| Maps | Leaflet.js | Farm/project location |
| Charts | Chart.js 4.4.0 | Growth curves, predictions |
| Icons | Font Awesome 6 subset | 159 curated icons |
| Animations | Animate.css subset | 6 entrance animations |

Build pipeline:
```bash
npm run build:tailwind   # Tailwind → baay/static/css/tailwind.css
npm run build:fa         # FA subset → baay/static/css/fa-subset.css + webfonts
npm run build:css        # Both in sequence
```

---

## Design Principles

1. **Sahel-first** — designed for low-bandwidth, small screens, and outdoor visibility
2. **Generous radii** — everything is rounded (22px cards, 40px pills) for a friendly feel
3. **Glass & gradients** — glass morphism + green gradients as the signature look
4. **Token-driven** — every color, radius, shadow, and spacing uses CSS custom properties
5. **Dark mode native** — not an afterthought; both themes are first-class
6. **Progressive enhancement** — works without JS (Django templates), enriched with Alpine/HTMX
7. **Accessible by default** — focus rings, ARIA, skip links, 44px touch targets
8. **Performance-conscious** — vendor subsets, lazy loading, local assets over CDNs

---

## File Organization

```
baay/static/
├── css/
│   ├── _src/               Tailwind input source
│   ├── base.css            ★ Master design tokens + base components
│   ├── base-inline.css     Critical-path inline styles
│   ├── mobile.css          Touch-first mobile utilities
│   ├── mobile-agri-pages.css  Mobile overrides for agri pages
│   ├── navbar-responsive.css  Responsive navbar + drawer
│   ├── rounded-global.css  Vendor widget rounding
│   ├── tailwind.css        Built Tailwind output (tw- prefix)
│   ├── fa-subset.css       Font Awesome icon subset
│   ├── animate-subset.css  Animate.css subset
│   ├── dashboard*.css      Dashboard page styles
│   ├── projects*.css       Project list/detail styles
│   ├── farm-cards.css      Farm card components
│   ├── finance*.css        Finance hub styles
│   ├── messagerie*.css     Messaging UI
│   └── ...                 Other page-specific CSS
├── icons/                  PWA icons (192, 512, apple-touch)
├── images/                 Brand assets, photos
│   ├── anddbaay-logo-wordmark.svg
│   ├── anddbaay-mark.svg
│   └── anddbaay-mark-mono.svg
└── js/                     JavaScript files
    └── sw.js               Service worker

templates/
├── base.html               ★ Master layout (nav, footer, modals, scripts)
├── base_mini.html          Minimal layout (auth pages)
├── home.html               Landing page
├── includes/               Shared partials (brand, toasts, PWA meta)
├── admin/                  Admin customizations
├── auth/                   Login, registration, password reset
├── dashboard/              Dashboard variants by role
├── projets/                Project CRUD + detail
├── fermes/                 Farm management
├── semis/                  Sowing management
├── taches/                 Task management
├── finance/                Finance hub
├── messagerie/             Real-time messaging
├── sols/                   Soil analysis
├── marketplace/            Marketplace
└── ...
```
