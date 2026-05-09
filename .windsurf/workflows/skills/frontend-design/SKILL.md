---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build or improve UI for this Django app (templates + CSS), including FinanceHub and dashboard pages. Apply cohesive typography/color/motion/layout decisions, fix UX/a11y issues, and implement real working code that avoids generic AI aesthetics.
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic \"AI slop\" aesthetics, adapted for this repository (Django templates in `templates/` and CSS/JS in `baay/static/`).

## When to use
- When the user asks to **assess**, **improve**, **beautify**, **redesign**, or **polish** UI/UX.
- When editing **FinanceHub** (`templates/finance/finance_list.html`, `baay/static/css/finance_hub_ft.css`) or **Dashboard** (`templates/projets/dashboard*.html`, `baay/static/css/dashboard*.css`).
- When adding or updating UI patterns: cards, tables, filters, forms, empty/loading states, modals/confirmations.

## Design thinking (mandatory)
Before changing code, commit to a clear aesthetic direction:
- **Purpose**: what the page helps the user do (ops cockpit, finance entry, monitoring).
- **Tone**: pick a deliberate aesthetic (refined/utilitarian, editorial, organic, etc.).
- **Constraints**: Django templates, existing tokens in `templates/base.html`, dark mode via `html.dark-mode`, mobile/touch support, accessibility.
- **Differentiation**: 1 memorable detail (composition, texture, motion, typography, or a signature component).

**CRITICAL**: Intentionality over intensity. The goal is a cohesive system, not random effects.

## Project-specific guardrails
- **Respect existing tokens and theming**: prefer variables like `--text-main`, `--text-muted`, `--card-bg`, `--border-color`, `--accent` and FinanceHub `--fh-*` tokens; add new variables only when needed.
- **Dark mode parity**: every new surface must look correct in both light and dark mode; never leave light-only backgrounds in dark mode.
- **Accessibility**:
  - Don’t rely on hover-only interactions; ensure keyboard and touch equivalents (`:focus-within`, `@media (hover:none)`).
  - Ensure focus rings are visible (`:focus-visible`).
  - Provide good contrast; avoid “washed out” text in dark mode.
- **Consistency**:
  - Avoid mixing multiple UI languages inside a page (e.g., Tailwind utility fragments vs bespoke CSS) unless it’s clearly scoped.
  - Reuse existing patterns (pills, cards, tables) rather than inventing new ones per page.
- **Performance**: keep effects lightweight; prefer CSS over heavy JS; avoid large new dependencies.

## Implementation workflow
1. **Audit** the page quickly:
   - hierarchy, density, primary actions, error/empty/loading states
   - a11y (keyboard, focus, touch, contrast)
   - consistency with the rest of the app
2. **Propose a small set of corrections** (3–7 bullets) prioritized by impact.
3. **Implement** changes in templates/CSS:
   - templates in `templates/**`
   - styles in `baay/static/css/**`
   - scripts only when necessary in `baay/static/js/**` or inline (avoid large inline scripts)
4. **Verify**:
   - `python manage.py check`
   - visually sanity-check light + dark mode and mobile widths

## Common high-impact corrections (templates/CSS)
- Make filter + results behavior consistent (if totals update live, results should too).
- Replace `confirm()` with a styled dialog pattern if the page is “premium UI”.
- Use sticky headers for long tables.
- Normalize money formatting (use the repo’s `|fcfa` template filter where applicable).
- Reduce visual noise: fewer competing gradients/shadows; reserve strong motion for 1–2 moments.

