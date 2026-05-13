# Fix Critical XSS — Items #2, #3, #5

Replace `innerHTML` with template literals containing unsanitized API data in `dashboard.js` and `projects.js` using a shared `escapeHtml()` utility and DOM construction where inline handlers are involved.

---

## Item #2: Dashboard project modal (`dashboard.js:1635-1644`)

**Current (broken):**
```js
modalList.innerHTML = projectsToShow.map(project => `
    <div class="modal-project-item" onclick="window.location.href='/projet/${project.id}/'">
        <div class="modal-project-info">
            <h4>${project.nom}</h4>
            <p>${project.cultureName || 'Culture'} - ${project.localite || 'Localité'}</p>
        </div>
        <div class="modal-project-stats">
            <span><i class="fas fa-crop-alt"></i> ${project.superficie} ha</span>
            <span><i class="fas fa-weight"></i> ${project.rendement} kg</span>
        </div>
    </div>
`).join('');
```

**Fix approach:**
1. Add a `escapeHtml()` utility at the top of `dashboard.js` (or import from `base.js`).
2. Replace the `innerHTML` + template literal with DOM construction using `document.createElement` + `textContent`.
3. Remove inline `onclick` — attach event listener via `addEventListener`.

**Why DOM construction over `escapeHtml`?** Because there are ~6 values to escape plus an inline handler. DOM construction is cleaner and eliminates the handler risk entirely.

---

## Item #3: Dashboard project list (`dashboard.js:2262-2284`)

**Current (broken):**
```js
return `
<div class="project-item" data-id="${p.id}" ...>
    <div class="project-info" onclick="window.location.href='/projet/${p.id}/'">
        <div class="project-name editable" data-id="${p.id}"
            ondblclick="editProjectName(event, '${p.id}', '${p.nom.replace(/'/g, "\\'")}')">
            ${p.nom}
        </div>
        ...
        <span><i class="fas fa-seedling"></i> ${p.culture_nom}</span>
```

**Fix approach:**
1. Same `escapeHtml()` utility.
2. Build the item via `document.createElement` instead of `innerHTML`.
3. Remove inline `onclick` and `ondblclick` — use `addEventListener` for both.
4. The `editProjectName` call should pass the raw `p.nom` string, not an HTML-escaped version.

**Key challenge:** The current code returns a string from `listHtml` that is later assigned to `innerHTML`. We'll need to change the caller to append DOM nodes instead of setting `innerHTML`.

---

## Item #5: Quick view modal (`projects.js:654-724`)

**Current (broken):**
```js
document.getElementById('quickViewContent').innerHTML = `
    <div class="modal-detail-row">
        <span class="modal-detail-label">Culture</span>
        <span class="modal-detail-value">${culture}</span>
    </div>
    ...
`;
```

**Fix approach:**
1. Use `escapeHtml()` utility since this is a simple static structure with a few values.
2. Apply `escapeHtml()` to `culture`, `progress`, `statusLabel`, `superficie`, `date`, `localite`, `budget`.

**Why `escapeHtml` here?** The structure is static and the values are simple strings. `escapeHtml` + template literal is less code than full DOM construction for ~10 rows of HTML.

---

## Shared `escapeHtml` utility

**Location:** Add to `base.js` (if not already present) and make it available globally:
```js
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML;
}
```

`dashboard.js` and `projects.js` can call it directly (they already run in the same page context).

---

## Files to modify

| File | Lines | Change |
|------|-------|--------|
| `baay/static/js/dashboard.js` | ~1635-1644 | DOM construction for modal items |
| `baay/static/js/dashboard.js` | ~2262-2284 | DOM construction for project list items + remove inline handlers |
| `baay/static/js/projects.js` | ~592 | Fix inline edit `innerHTML` (bonus: item #4 is adjacent) |
| `baay/static/js/projects.js` | ~654-724 | `escapeHtml()` for quick view modal |
| `baay/static/js/base.js` | top of file | Add `escapeHtml()` utility |

---

## Testing checklist

- [ ] Create a project with name containing `<script>alert(1)</script>`
- [ ] Open dashboard → project list renders without executing JS
- [ ] Open dashboard → project modal renders without executing JS
- [ ] Open project list → quick view renders without executing JS
- [ ] Double-click to edit project name still works
- [ ] Click to navigate to project detail still works
- [ ] Check on mobile (320px-768px) that layout doesn't break
- [ ] Verify `escapeHtml` doesn't break French characters (accents, cedilla)

---

## Mobile considerations (per stored rule)

- The project list is already responsive (horizontal scroll + grid)
- DOM construction preserves existing CSS classes, so no layout changes
- Ensure tap targets remain ≥ 44×44px (the existing `.project-item` already has generous padding)
