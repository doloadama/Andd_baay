# Design Fix TODO

## Completed ✅
- [x] Created `baay/static/CSS/base.css` (extracted from base.html)
- [x] Fixed CSS syntax error (comment)
- [x] Updated base.html to load external CSS
- [x] Test: `python manage.py collectstatic --dry-run`

## Next Steps
1. Extract dashboard.css from templates/projets/dashboard.html <style>
2. Extract home.css from templates/home.html <style>
3. Extract projet-detail.css from templates/projets/detail_projet.html
4. Extract auth.css from templates/auth/login.html
5. Delete all inline <style> blocks
6. Run `python manage.py collectstatic`
7. Test `python manage.py runserver`
8. Delete fix_*.py scripts
9. `attempt_completion`

