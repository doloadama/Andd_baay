# Frontend Security Audit — Andd Baay

> Date: May 13, 2026
> Scope: Frontend code (HTML templates, JavaScript, CSS) + Django settings
> Severity: 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low

---

## 🔴 Critical: XSS via `innerHTML` with unsanitized data

### 1. Chat widget (`base.js:283`)
```js
contentEl.innerHTML = text.replace(/\n/g, '<br>');
```
**Risk**: `text` comes from the chat API response and is directly assigned to `innerHTML`. If the backend returns unsanitized user input or an attacker manipulates the API response, arbitrary HTML/JS will execute.

**Fix**: Use `textContent` instead of `innerHTML`:
```js
contentEl.textContent = text;
contentEl.style.whiteSpace = 'pre-line'; // preserves line breaks safely
```

---

### 2. Dashboard project modal (`dashboard.js:1635-1639`)
```js
modalList.innerHTML = projectsToShow.map(project => `
    <div class="modal-project-item" onclick="window.location.href='/projet/${project.id}/'">
        <h4>${project.nom}</h4>
        <p>${project.cultureName || 'Culture'} - ${project.localite || 'Localité'}</p>
```
**Risk**: `project.nom`, `project.cultureName`, `project.localite`, `project.superficie`, `project.rendement` are inserted without HTML escaping. If project names contain `<script>` tags, they execute.

**Fix**: Use DOM construction instead of template literals:
```js
const div = document.createElement('div');
const h4 = document.createElement('h4');
h4.textContent = project.nom;
div.appendChild(h4);
// ... etc
```

Or add an `escapeHtml()` utility and apply it to all interpolated values.

---

### 3. Dashboard project list (`dashboard.js:2262-2284`)
```js
return `
<div class="project-item" data-id="${p.id}" data-status="${p.statut}" ...>
    <div class="project-info" onclick="window.location.href='/projet/${p.id}/'">
        <div class="project-name editable" data-id="${p.id}"
            ondblclick="editProjectName(event, '${p.id}', '${p.nom.replace(/'/g, "\\'")}')">
            ${p.nom}
        </div>
        <div class="project-meta">
            ${farmBadge}
            <span><i class="fas fa-seedling"></i> ${p.culture_nom}</span>
```
**Risk**: Multiple unsanitized values (`p.nom`, `p.culture_nom`, `p.ferme_nom`) + the `replace(/'/g, "\\'")` only escapes single quotes — it does NOT escape `<`, `>`, `&`, `"`. If `p.nom` contains `" onclick="alert(1)`, it breaks out of the `ondblclick` attribute.

**Fix**: Remove inline `onclick`/`ondblclick` handlers entirely. Use `addEventListener`:
```js
div.addEventListener('click', () => { window.location.href = `/projet/${encodeURIComponent(p.id)}/`; });
nameDiv.addEventListener('dblclick', () => editProjectName(p.id, p.nom));
```

---

### 4. Inline project name edit (`projects.js:592`)
```js
cell.innerHTML = `<input type="text" class="project-name-input" value="${original}" aria-label="Modifier le nom du projet">`;
```
**Risk**: `original` comes from `cell.dataset.original || cell.textContent.trim()`. If a project name contains `"`, it breaks out of the `value` attribute. If it contains `><script>alert(1)</script>`, it executes.

**Fix**: Use DOM construction:
```js
const input = document.createElement('input');
input.type = 'text';
input.className = 'project-name-input';
input.value = original;
input.setAttribute('aria-label', 'Modifier le nom du projet');
cell.innerHTML = '';
cell.appendChild(input);
```

---

### 5. Quick view modal (`projects.js:654`)
```js
document.getElementById('quickViewContent').innerHTML = `
    <div class="modal-detail-row">
        <span class="modal-detail-label">Culture</span>
        <span class="modal-detail-value">${culture}</span>
```
**Risk**: `culture` comes from DOM `textContent` but is then inserted via `innerHTML`. If DOM text was poisoned with HTML, it renders.

**Fix**: Use `textContent` for all values, or DOM construction.

---

## 🟠 High: Supply chain / external script risks

### 6. Figma capture script without SRI (`base.html:97`)
```html
<script src="https://mcp.figma.com/mcp/html-to-design/capture.js" async></script>
```
**Risk**: External script loaded without Subresource Integrity. If Figma's CDN is compromised, arbitrary JavaScript executes on your domain with full access to cookies, localStorage, and the DOM.

**Fix**: Either remove (it's commented out in the head but uncommented lower) or add SRI hash:
```html
<script src="https://mcp.figma.com/mcp/html-to-design/capture.js"
    integrity="sha384-..."
    crossorigin="anonymous" async></script>
```

---

### 7. Google Fonts without SRI (`base.html:32-36`)
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=..." rel="stylesheet">
```
**Risk**: Lower than Figma, but still a supply chain vector. Google Fonts has been used for tracking/fingerprinting.

**Fix**: Self-host fonts, or add `&display=swap` and consider `dns-prefetch` instead of `preconnect`.

---

## 🟡 Medium: Data exposure & missing protections

### 8. Chat history in unencrypted localStorage (`base.js:252-272`)
```js
localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(toSave));
const saved = localStorage.getItem(CHAT_HISTORY_KEY);
```
**Risk**: Chat messages are persisted in localStorage. Not encrypted, accessible to any JavaScript running on the domain (including XSS payloads). If an attacker gains XSS, they can read all chat history.

**Fix**: Do not store sensitive conversations in localStorage. If persistence is required, use sessionStorage (cleared on tab close) or encrypt with a user-derived key.

---

### 9. Missing CSP meta tag fallback (`base.html`)
No `<meta http-equiv="Content-Security-Policy" content="...">` in the HTML. While Django middleware sets CSP headers via `baay.middleware.csp.ContentSecurityPolicyMiddleware`, a meta tag provides defense-in-depth and protects before the response is fully processed.

**Fix**: Add a strict CSP meta tag:
```html
<meta http-equiv="Content-Security-Policy"
    content="default-src 'self'; script-src 'self' 'unsafe-inline' https://mcp.figma.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' wss://your-domain.com;">
```

---

### 10. Missing referrer policy meta tag (`base.html`)
No `<meta name="referrer" content="strict-origin-when-cross-origin">` or similar. Leaked referrer headers can expose internal URLs to third-party sites.

**Fix**: Add:
```html
<meta name="referrer" content="strict-origin-when-cross-origin">
```

---

## 🟢 Low / Informational

### 11. `eval()` / `Function()` / `document.write()` — None found ✅
No dangerous dynamic code execution patterns detected in custom JS.

### 12. `setTimeout` with strings — None found ✅
No `setTimeout('string')` patterns detected.

### 13. localStorage for non-sensitive data ✅
- Theme preference (`theme`) — benign
- Tour completion (`tour`) — benign
- Projects view mode (`projectsView`) — benign
- Dashboard layout (`dashboardLayout_v2`) — benign
- Collapsed sections (`collapsedSections`) — benign
- Chat state (`chatState`) — benign

Only the **chat history** (`chatHistory`) is sensitive (see #8).

---

## ✅ Positive Security Findings

| Finding | Status | Details |
|---------|--------|---------|
| **CSRF tokens** | ✅ | Found in 40 form templates across 34 files. Django `CsrfViewMiddleware` active. |
| **No hardcoded secrets** | ✅ | `SECRET_KEY` from `DJANGO_SECRET_KEY` env var. `OPENWEATHER_API_KEY` from env var. |
| **Security headers** | ✅ | `X_FRAME_OPTIONS`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` all configured in production. |
| **CSP middleware** | ✅ | `baay.middleware.csp.ContentSecurityPolicyMiddleware` is in `MIDDLEWARE`. |
| **Origin check in PJAX** | ✅ | `pjax.js` validates `new URL(href, window.location.href).origin === window.location.origin` before intercepting clicks. |
| **Messagerie uses `escapeHtml`** | ✅ | `messagerie-conversation.js:80-84` has a proper `escapeHtml()` using `textContent` → `innerHTML` trick. |
| **Debug toolbar gated** | ✅ | Only active when `DEBUG=True` and `not IS_VERCEL`. Hidden for HTMX requests. |
| **Strong SECRET_KEY validation** | ✅ | Raises if key starts with `django-insecure-` or is < 50 chars in production. |

---

## Summary: Risk Matrix

| # | Issue | Severity | File | Effort to fix |
|---|-------|----------|------|---------------|
| 1 | Chat widget `innerHTML` XSS | 🔴 Critical | `base.js:283` | 5 min |
| 2 | Dashboard modal `innerHTML` XSS | 🔴 Critical | `dashboard.js:1635` | 20 min |
| 3 | Dashboard list `innerHTML` + inline handlers | 🔴 Critical | `dashboard.js:2262` | 30 min |
| 4 | Inline edit `innerHTML` XSS | 🔴 Critical | `projects.js:592` | 10 min |
| 5 | Quick view `innerHTML` XSS | 🔴 Critical | `projects.js:654` | 10 min |
| 6 | Figma script without SRI | 🟠 High | `base.html:97` | 5 min |
| 7 | Google Fonts without SRI | 🟠 High | `base.html:32` | 15 min |
| 8 | Chat history in localStorage | 🟡 Medium | `base.js:252` | 15 min |
| 9 | Missing CSP meta tag | 🟡 Medium | `base.html` | 10 min |
| 10 | Missing referrer policy | 🟡 Medium | `base.html` | 2 min |

---

## Recommended immediate actions

1. **Replace all `innerHTML` with DOM APIs** (`createElement` + `textContent`) wherever user/project data is rendered.
2. **Add a shared `escapeHtml()` utility** to `base.js` and use it in all template literal → `innerHTML` paths.
3. **Remove all inline `onclick`/`ondblclick` handlers** from dynamically generated HTML — use `addEventListener`.
4. **Add SRI or remove** the Figma capture script.
5. **Add CSP meta tag** and `referrer` meta tag to `base.html`.
6. **Stop storing chat history in localStorage** — use `sessionStorage` or don't persist.
