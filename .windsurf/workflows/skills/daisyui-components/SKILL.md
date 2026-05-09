---
name: daisyui-components
description: Select and integrate daisyUI (Tailwind) components into this repo’s Django templates and CSS while preserving the existing design tokens, dark mode behavior (html.dark-mode), accessibility (no hover-only), and performance. Use when the user mentions daisyUI, DaisyUI, Tailwind components, or asks to add UI components like modal, dropdown, drawer, tabs, table, badge, alert, toast, or forms.
disable-model-invocation: true
---

# daisyui-components

## Scope

This project primarily uses Django templates in `templates/` and custom CSS in `baay/static/css/` with an existing token system (e.g. `--text-main`, `--card-bg`, `--border-color`, `--accent`, and FinanceHub `--fh-*` tokens) and dark mode via `html.dark-mode`.

Use daisyUI as a **component vocabulary** (structure + utility class conventions), not as a competing theme system.

## Guardrails (must follow)

- **Do not introduce daisyUI global theming conflicts**
  - Avoid `theme-controller` and theme switching unless explicitly requested.
  - Don’t add global `data-theme` dependencies that fight `html.dark-mode`.
- **Keep token consistency**
  - Prefer existing CSS variables over hard-coded colors.
  - If using daisyUI classes that imply colors (`btn-primary`, `alert-success`), either map them to existing tokens via scoped CSS or use neutral variants and apply tokens yourself.
- **Accessibility**
  - No hover-only interactions: include keyboard/touch equivalents (`:focus-visible`, `:focus-within`, `@media (hover:none)`).
  - Ensure dialogs/menus are reachable and dismissible via keyboard.
- **Performance**
  - Prefer CSS-only patterns; avoid adding new JS unless necessary.
  - If JS is required, keep it small and colocate it in `baay/static/js/` (or minimal inline only when unavoidable).

## Workflow

1. **Identify the UI need**
   - Component type: modal, dropdown, drawer, tabs, table, alert/toast, badge/status, form field.
   - Interaction: click, keyboard navigation, touch behavior.
   - State: empty/loading/error.

2. **Choose a daisyUI component pattern**
   - Start from the daisyUI component page list: `https://daisyui.com/components/`.
   - Prefer the simplest variant that matches requirements.

3. **Adapt it to this repo**
   - Put markup in `templates/**`.
   - Put styling in `baay/static/css/**`, scoped to a page/root container when possible.
   - Map colors/spacing to the project’s tokens.

4. **A11y + dark-mode parity**
   - Verify focus rings.
   - Verify on narrow mobile widths.
   - Verify `html.dark-mode` renders correctly (no light-only surfaces).

5. **Verify**
   - Run: `python manage.py check`.
   - Do a quick visual sanity check of the component in both light and dark mode.

## Quick component routing (what to use)

- **Confirmation / destructive actions**: `modal`
- **Inline actions list**: `dropdown`
- **Mobile navigation/sidebar**: `drawer`
- **Status labeling**: `badge` (or `status` for tiny dot indicators)
- **Flash messages**: `alert` or `toast`
- **Long data lists**: `table` (+ sticky header in CSS when needed)
- **Grouped controls**: `join`, `tabs`, `fieldset`
- **Loading states**: `loading` or `skeleton`

## Integration notes for this repo

- **Avoid “UI dialect mixing” inside one component**
  - If a page is already bespoke (e.g., FinanceHub), keep daisyUI usage limited and style it to match existing patterns.
- **Prefer scoping**
  - If you must override daisyUI classes, scope them under a page root (e.g. `.finance-ft-root …`) to avoid cross-page regressions.

