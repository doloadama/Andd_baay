# Fix Django TemplateSyntaxError Plan

## Steps:
1. ✅ Understand issue: Escaped quotes in {% static 'js/base.js' %} in templates/base.html
2. ✅ Edit templates/base.html to fix `{% static \'js/base.js\' %}` → `{% static 'js/base.js' %}`
3. ✅ Verify no other occurrences using search_files (0 results found)
4. Test the fix (restart server, check /semis/)
5. Mark complete
