# Andd Baay — Design System

> **Premium Afro-Tech** aesthetic — a modern agricultural platform blending West African warmth with clean tech interfaces.

---

## 1. Brand Identity

| Attribute       | Value                                                        |
| --------------- | ------------------------------------------------------------ |
| **Name**        | Andd Baay (Wolof: *"cultivate well"*)                        |
| **Tagline**     | L'agriculture de demain                                      |
| **Personality** | Professional, warm, trustworthy, technically advanced         |
| **Audience**    | Sahelian farmers & agricultural cooperatives (Senegal focus)  |
| **Languages**   | French (primary), English                                    |
| **PWA**         | Installable on mobile, basic offline mode with service worker |

---

## 2. Color Palette

### Brand Colors

| Token              | Hex       | Role                              |
| ------------------ | --------- | --------------------------------- |
| `--brand-primary`  | `#1D9E75` | Primary actions, links, accents   |
| `--brand-deep`     | `#085041` | Gradient endpoints, hover states  |
| `--brand-night`    | `#04342C` | Hero backgrounds, dark anchors    |
| `--brand-pale`     | `#9FE1CB` | Subtle highlights, tags           |
| `--brand-light`    | `#5DCAA5` | Dark-mode accent, hover highlight |
| `--brand-bg`       | `#E1F5EE` | Light-mode page background        |
| `--brand-accent`   | `#EF9F27` | CTAs, warnings, saffron/ochre     |

### Functional Aliases

```
--primary     → --brand-primary
--accent      → --brand-primary  (--brand-light in dark mode)
--accent-dark → --brand-deep
--danger      → #ef4444
--success     → #1D9E75
--info        → #3b82f6
--warning     → #EF9F27
```

### Subtle Backgrounds (12-14% opacity)

```
--danger-subtle   rgba(239, 68, 68, 0.12)
--success-subtle  rgba(29, 158, 117, 0.12)
--warning-subtle  rgba(239, 159, 39, 0.14)
--info-subtle     rgba(59, 130, 246, 0.12)
--accent-subtle   rgba(29, 158, 117, 0.14)
```

### Light Mode (Default)

```
--bg-deep        #E1F5EE      Page background
--bg-secondary   #f4fbf8      Card secondary / alternating rows
--bg-tertiary    #d8efe6      Deeper insets
--card-glass     rgba(255,255,255,0.92)
--card-bg-solid  #ffffff
--text-main      #2C2C2A
--text-secondary #454542
--text-muted     #5c5c57
--border-glass   rgba(8,80,65,0.1)
--glass-bg       rgba(255,255,255,0.88)
```

### Dark Mode

Activated via `html.dark-mode` + `data-bs-theme="dark"`. System preference auto-detected; user toggle persisted in `localStorage('theme')`. Anti-flash script in `<head>` prevents FOUC.

```
--bg-deep        #0a0f0e
--bg-secondary   #121c19
--card-glass     rgba(18,28,25,0.85)
--text-main      #E8F5F0
--text-muted     #8aa89e
--border-glass   rgba(93,202,165,0.12)
```

---

## 3. Typography

| Role       | Family                          | Weights   | Usage                            |
| ---------- | ------------------------------- | --------- | -------------------------------- |
| **Body**   | `Inter`                         | 400–700   | All body text, forms, UI labels  |
| **Display**| `Space Grotesk`                 | 400–700   | Headings, buttons, page titles   |
| **Fallback**| `Plus Jakarta Sans` → `sans-serif` | 400, 700 | Loaded but rarely targeted       |

### Scale

```
Page title        1.75rem / 800wt / Space Grotesk / letter-spacing -0.02em
Section title     1.125rem / 700wt
Body              0.9375rem / 400wt
Small / meta      0.85rem / 600wt / uppercase / letter-spacing 0.05-0.08em
Tiny (badges)     0.75rem / 800wt / uppercase
```

---

## 4. Spacing & Layout

### Spacing Scale (CSS custom properties)

```
--space-1   4px      --space-5   20px
--space-2   8px      --space-6   24px
--space-3   12px     --space-7   28px
--space-4   16px     --space-8   32px
                     --space-10  40px
```

### Layout Containers

| Container           | Max-width | Padding          |
| -------------------- | --------- | ---------------- |
| `.container-modern`  | 1280px    | 32px / 20px (mobile: 20px / 16px) |
| `.center-wrap`       | 480px     | Centered forms   |
| `.container-narrow`  | 1180px    | Landing page     |

### Grid System

- **Bootstrap 5.3** grid for page layout
- **CSS Grid** for dashboard stat cards (`grid-template-columns` responsive)
- **Flexbox** everywhere else with `flex-wrap` for safety

---

## 5. Border Radii

A generous, rounded visual language — feels modern and approachable.

| Token            | Value   | Used for                     |
| ---------------- | ------- | ---------------------------- |
| `--radius-xs`    | `6px`   | Tooltips                     |
| `--radius-sm`    | `10px`  | Small elements               |
| `--radius-input` | `12px`  | Inputs, dropdowns, accordions, badges |
| `--radius-tight` | `14px`  | Buttons, bottom-sheet links  |
| `--radius-md`    | `16px`  | Inner cards                  |
| `--radius-lg-ui` | `18px`  | Larger UI surfaces           |
| `--radius-card`  | `22px`  | Primary cards, modals        |
| `--radius-xl`    | `28px`  | Oversized surfaces           |
| `--radius-panel` | `32px`  | Full panels                  |
| `--radius-pill`  | `40px`  | Pill buttons, status chips, tags |

All Bootstrap component radii are overridden via CSS custom properties to match (see `base.css :root`).

Vendor widgets (Leaflet popups/controls) are also rounded via `rounded-global.css`.

---

## 6. Shadows & Elevation

```
--shadow-sm    0 2px 8px   rgba(8,80,65,0.06)     Cards at rest
--shadow-md    0 4px 16px  rgba(8,80,65,0.08)     Hover / elevated
--shadow-lg    0 12px 32px rgba(8,80,65,0.12)      Modals, drawers
--shadow-glow  0 10px 30px rgba(29,158,117,0.12)   Glass cards, hero
```

Dark mode swaps to pure black shadows (`rgba(0,0,0,0.2-0.4)`).

---

## 7. Transitions & Motion

```
--transition       0.3s cubic-bezier(0.4, 0, 0.2, 1)    Standard
--transition-fast  0.15s cubic-bezier(0.4, 0, 0.2, 1)    Micro-interactions
```

- **Hover lift**: `translateY(-2px)` to `translateY(-4px)` on interactive cards
- **Animate.css subset**: 6 animations used (`fadeIn`, `fadeInDown`, etc.) — loaded from local subset (~65 KB savings)
- Alpine.js `x-transition` for dropdowns, bottom sheets, offline indicator

---

## 8. Component Library

### Buttons

| Class                  | Style                                    |
| ---------------------- | ---------------------------------------- |
| `.btn-baay-primary`    | Green gradient → white text, glow shadow |
| `.btn-baay-secondary`  | Orange/saffron gradient                  |
| `.btn-baay-outline`    | Transparent + border                     |
| `.btn-baay-ghost`      | Transparent, muted text                  |
| `.btn-modern`          | Pill-shaped variant                      |
| `.btn-accent`          | Green gradient (used in context)         |
| `.btn-outline-modern`  | Thin border, no fill                     |

### Cards

| Class          | Description                                  |
| -------------- | -------------------------------------------- |
| `.glass-card`  | Frosted glass with `backdrop-filter: blur(14px)`, border, glow shadow |
| `.surface-card`| Solid background, used for centered forms    |
| `.dash-stat-card` | KPI stat card with hover lift             |
| `.farm-card`   | Horizontal scrollable farm overview card     |

### Status Chips

```css
.status-chip.en_cours  → blue-subtle
.status-chip.en_pause  → orange-subtle
.status-chip.fini      → green-subtle
```

### Tags / Pills

```css
.tag             → Neutral bordered pill
.tag-accent      → Green-tinted
.tag-success     → Green-tinted (slightly different alpha)
```

### Tables

`.table-modern` — full-width with rounded borders, striped odd rows, hover highlight, uppercase headers.

### Empty States

`.empty-state` — centered layout with icon box (`.empty-state-icon`), title, description, and action button.

### Alerts & Toasts

- `.alert-modern` — rounded card-style alert
- `.toast` — with colored `.toast-icon` (success/error variants)

---

## 9. Page-Level Patterns

### Navigation (Navbar)

- **Desktop**: Floating navbar (`.navbar-floating`) with dropdown menus via Alpine.js
- **Mobile**: Hamburger → full-screen drawer + bottom navigation sheet
- Theme toggle (moon/sun) in both desktop and mobile
- Language switcher (FR 🇫🇷 / EN 🇬🇧)
- Notification bell with unread badge and tabbed dropdown (Messages / System)
- User avatar with initials and profile dropdown

### Hero Headers (Project Detail)

Gradient background (`--brand-night → --brand-deep → --brand-primary`), white text, back button, status badge, meta row with icons.

### Dashboard Layout

- Header with title + "Live" indicator + date + actions
- Stat cards in responsive grid
- Section cards with headers (icon + title + badge)

### Forms

All inputs use:
- `border-radius: var(--radius-input)` (12px)
- `border: 1px solid var(--border-color)`
- `background: var(--bg-secondary)`
- Focus ring: `box-shadow: 0 0 0 4px rgba(29,158,117,0.15)`
- Labels: uppercase, `Space Grotesk`, 700wt, 0.85rem

### Onboarding Tour

Modal overlay with step progression, icon animation, progress bar, and skip/next actions.

---

## 10. Iconography

- **Font Awesome 6** — custom subset of **159 icons** (built via `fontawesome-subset` + `build-fa-subset.mjs`)
- Saves ~306 KB vs full CDN
- Icons referenced in `.fa-icons-used.txt`
- Style: outline (regular) and solid where emphasis is needed

### Common icon mapping

| Concept        | Icon                  |
| -------------- | --------------------- |
| Farms          | `fa-warehouse`        |
| Projects       | `fa-folder-open`      |
| Crops/Plants   | `fa-seedling`         |
| Tasks          | `fa-list-check`       |
| Finance        | `fa-wallet`, `fa-coins` |
| Weather        | `fa-cloud-sun`        |
| AI/Prediction  | `fa-robot`, `fa-bolt` |
| Map            | `fa-map-marked-alt`   |
| Soil Analysis  | `fa-flask`, `fa-vial` |
| Messages       | `fa-envelope`         |
| Notifications  | `fa-bell`             |

---

## 11. Mobile & Responsive Strategy

### Approach: **Mobile-first, progressive enhancement**

| Breakpoint     | Target                          |
| -------------- | ------------------------------- |
| `< 576px`      | Small phones — compact layout   |
| `< 768px`      | Mobile — bottom nav, drawer     |
| `768px–1024px`  | Tablet — 2-column grids        |
| `> 1024px`     | Desktop — full navbar, sidebars |

### Key Mobile Patterns

- **Bottom navigation** sheet (Alpine.js) replaces desktop sidebar
- **Touch targets**: minimum `44×44px` (`min-height: 44px` on buttons via `@media (pointer: coarse)`)
- **Horizontal scrolling**: stat cards, farm cards use `overflow-x: auto` + `scroll-snap-type`
- **Safe area insets**: `env(safe-area-inset-bottom)` for bottom sheets
- **No hover-only interactions**: all hover effects have fallback states

### Stylesheet layers

```
base.css              → Design tokens, base components
base-inline.css       → Critical inline styles (offline badge, tokens re-declaration)
mobile.css            → Bottom sheet, bottom nav, touch utilities
mobile-agri-pages.css → Farm/project mobile overrides
navbar-responsive.css → Mobile drawer, hamburger, responsive nav
rounded-global.css    → Vendor widget rounding (Leaflet)
```

### Page-specific CSS

Loaded per template via `{% block extra_css %}`:
- `dashboard.css` / `dashboard-v2.css`
- `projects.css` / `projects-v2.css`
- `projet-detail.css` / `projet-detail-modern.css`
- `farm-cards.css` / `semis-cards.css`
- `finance.css` / `finance_hub_ft.css`
- `messagerie-conversation.css` / `messagerie-drawer.css`
- `performance.css` / `activites.css`

---

## 12. Dark Mode

### Activation

1. Anti-flash `<script>` in `<head>` reads `localStorage('theme')` or system preference
2. Sets `html.dark-mode` class + `data-bs-theme="dark"` attribute
3. Updates `<meta name="theme-color">` (`#04342C` dark / `#E1F5EE` light)

### Strategy

All colors use CSS custom properties. The `.dark-mode` selector overrides:
- Background variables (deep blacks/greens)
- Text (light greens/whites)
- Borders (subtle green glow)
- Shadows (black-based)
- Accent shifts from `--brand-primary` → `--brand-light`

No component needs to explicitly check dark mode — the token system handles it automatically.

---

## 13. Accessibility

| Principle          | Implementation                                          |
| ------------------ | ------------------------------------------------------- |
| **Skip link**      | `.skip-link` → `#main`, visible on focus                |
| **Focus visible**  | `3px solid rgba(29,158,117,0.5)` with `3px` offset     |
| **ARIA**           | `aria-label`, `aria-expanded`, `role="menu"`, `aria-current="page"` throughout nav |
| **Touch targets**  | `min-height: 44px` on interactive elements              |
| **Color contrast** | Status colors chosen for WCAG AA against both themes    |
| **Reduced motion** | Transitions use `cubic-bezier` (no infinite animations except `livePulse` on `.live-dot`) |
| **Screen reader**  | `aria-hidden="true"` on decorative icons                |
| **Offline status** | `role="status"` + `aria-live="polite"` on offline badge |

---

## 14. Performance

Documented in `perf-audit.md`. Key decisions:

| Optimization                  | Savings     |
| ----------------------------- | ----------- |
| Font Awesome subset (159 icons) | ~306 KB   |
| Animate.css subset (6 anims)   | ~65 KB    |
| Bootstrap CSS vendored locally  | No CDN RTT |
| Chart.js lazy-loaded            | Deferred ~200 KB |
| Tailwind built with purge       | Minimal CSS |
| `backdrop-filter` used sparingly | GPU-friendly |

---

## 15. Tech Stack (Frontend)

| Layer       | Technology                | Notes                               |
| ----------- | ------------------------- | ----------------------------------- |
| Framework   | Django Templates          | Server-rendered HTML                |
| CSS Base    | Bootstrap 5.3.0 (local)  | Grid, utilities, modal, dropdown    |
| CSS Custom  | Hand-written CSS          | All design tokens + components      |
| Tailwind    | v3 (`tw-` prefix)        | Utility classes, preflight disabled  |
| JS          | Vanilla JS + Alpine.js   | Dropdowns, drawers, offline sync    |
| HTMX        | Loaded in head            | Progressive enhancement             |
| Maps        | Leaflet.js                | Farm/project location               |
| Charts      | Chart.js 4.4.0            | Growth curves, predictions          |
| Icons       | Font Awesome 6 subset     | 159 curated icons                   |
| Animations  | Animate.css subset        | 6 entrance animations               |

### Build Pipeline

```bash
npm run build:tailwind   # Tailwind → baay/static/css/tailwind.css
npm run build:fa         # FA subset → baay/static/css/fa-subset.css + webfonts
npm run build:css        # Both in sequence
```

---

## 16. Visual Identity Elements

### African Pattern Overlay

Subtle geometric SVG pattern (`african-pattern-overlay`) applied as `position: fixed` background. Inverted in light mode, full opacity in dark mode — gives a subtle cultural texture to every page.

### Glass Morphism

`.glass-card` — frosted glass effect (`backdrop-filter: blur(14px)`) with semi-transparent backgrounds. Used for primary content surfaces.

### Gradient Language

- **Hero/headers**: `135deg, --brand-night → --brand-deep → --brand-primary`
- **Primary buttons**: `135deg, --brand-primary → --brand-deep`
- **Accent buttons**: `135deg, --brand-accent → #d98a1c`
- **Weather card**: `135deg, #2d3a5a → #1e2740`

---

## 17. File Organization

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

---

## 18. Design Principles

1. **Sahel-first** — designed for low-bandwidth, small screens, and outdoor visibility
2. **Generous radii** — everything is rounded (22px cards, 40px pills) for a friendly feel
3. **Glass & gradients** — glass morphism + green gradients as the signature look
4. **Token-driven** — every color, radius, shadow, and spacing uses CSS custom properties
5. **Dark mode native** — not an afterthought; both themes are first-class
6. **Progressive enhancement** — works without JS (Django templates), enriched with Alpine/HTMX
7. **Accessible by default** — focus rings, ARIA, skip links, 44px touch targets
8. **Performance-conscious** — vendor subsets, lazy loading, local assets over CDNs
