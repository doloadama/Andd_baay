---
name: testing-andd-baay
description: Test the Andd Baay Django agricultural platform locally. Use when verifying UI changes, security fixes, API behavior, or template rendering.
---

# Testing Andd Baay Locally

## Prerequisites

- Python 3.12+ with virtualenv
- The repo cloned at the standard location

## Local Setup (SQLite — no external DB needed)

The app falls back to SQLite when no `DATABASE_URL` or `ENV=production` is set.

```bash
cd /home/ubuntu/repos/Andd_baay
source env/bin/activate  # or create: python -m venv env && source env/bin/activate
pip install -r requirements.txt

# Set a dummy secret key (local dev only)
export DJANGO_SECRET_KEY="test-secret-key-for-local-development-only-not-production-use-1234567890"

# Run migrations (creates db.sqlite3)
python manage.py migrate

# Create a test superuser
python manage.py createsuperuser --username testuser --email test@test.com --noinput

# Set password via shell
python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'Andd_Baayi.settings'
import django; django.setup()
from django.contrib.auth.models import User
u = User.objects.get(username='testuser')
u.set_password('TestPass123!')
u.save()
print('Password set')
"

# Start dev server
python manage.py runserver 0.0.0.0:8000
```

## Test Credentials

- **Username/email**: `test@test.com`
- **Password**: `TestPass123!`
- Login page: `http://localhost:8000/login/`

## Key URLs

| URL | Description |
|-----|-------------|
| `/login/` | Login page |
| `/logout/` | Logout (POST only — GET returns 405) |
| `/dashboard/` | Main dashboard (requires login + farm) |
| `/onboarding/` | Shown after first login if no farm exists |
| `/register/` | Registration page |
| `/performance/?ferme=<id>` | Redirects to dashboard with tab param |
| `/activites/?ferme=<id>` | Redirects to dashboard with tab param |
| `/api/projet/creer/` | API endpoint for project creation |
| `/fermes/creer/` | Create a new farm |
| `/admin/` | Django admin (superuser only) |

## Testing Patterns

### Dark Mode Testing

Dark mode is toggled via the theme button in the navbar (gear/sun/moon icon, typically `devinid="8"` on authenticated pages). It adds/removes `.dark-mode` class on `<html>`.

**Toggle mechanism**: The button calls JS that toggles `.dark-mode` on `document.documentElement` and saves preference to `localStorage` (key: `theme`).

**CSS architecture**: The app uses two layers of CSS variables:
1. `base.css` / `base-inline.css` — global variables (`--bg-deep`, `--text-main`, etc.) with `.dark-mode` overrides
2. Template-specific inline `<style>` blocks (e.g., `dashboard_unified.html` uses `--at-*` variables) — these MUST have their own `.dark-mode` overrides or they'll stay light-themed

**Verifying CSS variables programmatically** (browser console):
```javascript
// Check if dark mode is active
document.documentElement.classList.contains('dark-mode')

// Check dashboard-specific variables
getComputedStyle(document.documentElement).getPropertyValue('--at-surface').trim()
// Expected dark: #121c19, Expected light: #ffffff

getComputedStyle(document.documentElement).getPropertyValue('--at-text').trim()
// Expected dark: #E8F5F0, Expected light: #2C2C2A

getComputedStyle(document.documentElement).getPropertyValue('--at-bg').trim()
// Expected dark: #0a0f0e, Expected light: #f8faf9
```

**Pages to check in dark mode**:
- `/login/` — form fields, labels, buttons
- `/register/` — form fields, labels, legal links
- `/` (landing) — hero, feature cards, FAQ accordion
- `/dashboard/` — KPI cards, tabs, topbar buttons, dropdown menu, project rows, site cards

**Known issue**: Dark mode preference might not persist across login redirects. After logging in, you may need to re-toggle dark mode on the dashboard. This is a pre-existing UX issue.

**HSTS cache issue**: Chrome may force HTTPS on `127.0.0.1` if HSTS was cached. Fix: navigate to `chrome://net-internals/#hsts`, delete `127.0.0.1` from the HSTS set.

### Cookie Headers
```bash
curl -sv http://localhost:8000/login/ 2>&1 | grep -i 'set-cookie'
```
Expect: `HttpOnly`, `SameSite=Lax` on `csrftoken` and `sessionid`.

### Django Settings Verification
```bash
python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'Andd_Baayi.settings'
import django; django.setup()
from django.conf import settings
print('SESSION_COOKIE_HTTPONLY:', settings.SESSION_COOKIE_HTTPONLY)
print('CSRF_COOKIE_HTTPONLY:', settings.CSRF_COOKIE_HTTPONLY)
print('SOCIALACCOUNT_LOGIN_ON_GET:', settings.SOCIALACCOUNT_LOGIN_ON_GET)
"
```

### Serializer Field Verification
```bash
python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'Andd_Baayi.settings'
import django; django.setup()
from baay.serializers import FermeSerializer, ProjetSerializer
print('FermeSerializer fields:', FermeSerializer.Meta.fields)
print('ProjetSerializer exclude:', ProjetSerializer.Meta.exclude)
"
```

### Login + Authenticated Requests via curl
```bash
# Get CSRF token
CSRF=$(curl -s -c /tmp/cookies.txt http://localhost:8000/login/ | grep -oP 'name="csrfmiddlewaretoken" value="\K[^"]+') 
# Login
curl -s -b /tmp/cookies.txt -c /tmp/cookies.txt -X POST http://localhost:8000/login/ \
  -d "csrfmiddlewaretoken=$CSRF&username=test@test.com&password=TestPass123!" \
  -H "Referer: http://localhost:8000/login/" -o /dev/null -w "%{http_code}\n"
# Use session for authenticated requests
curl -sv -b /tmp/cookies.txt "http://localhost:8000/performance/?ferme=test-uuid" 2>&1 | grep Location
```

### Redirect URL Encoding Test
Test with XSS and CRLF payloads to verify `urlencode()` sanitization:
```bash
curl -sv -b /tmp/cookies.txt "http://localhost:8000/performance/?ferme=%3Cscript%3Ealert(1)%3C/script%3E" 2>&1 | grep Location
```
Expect: `<script>` tags percent-encoded in Location header.

## Known Limitations

- **Vercel preview** deployments might be behind Vercel SSO auth. Test locally if blocked.
- **Google OAuth**: Not configured locally — `SOCIALACCOUNT_LOGIN_ON_GET` setting can only be verified via Django settings, not runtime OAuth flow.
- **ML features**: Disabled locally (numpy/scikit-learn warning is expected and harmless).
- **Cloudinary**: Media uploads won't work locally without `CLOUDINARY_URL` env var. Use Django admin or direct DB for test data if needed.
- **WebSockets/Redis**: Not available locally with default setup. Messaging features won't work.
- New users land on `/onboarding/` and need to create a farm before accessing the dashboard.

## Devin Secrets Needed

None required for local testing. For Vercel preview testing, Vercel account credentials would be needed (not currently configured).
