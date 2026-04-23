import re

html_path = r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\liste_projets.html"

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Clean up inline styles
content = content.replace('style="width: 40px;"', 'class="col-checkbox"')
content = content.replace('style="width: 120px;"', 'class="col-actions"')
content = content.replace('style="width: 18px; height: 18px; accent-color: var(--accent); cursor: pointer;"', 'class="accent-checkbox pointer"')
content = content.replace('style="width: 18px; height: 18px; accent-color: var(--accent);"', 'class="accent-checkbox"')
content = content.replace('style="padding: 2px;"', 'class="p-1"')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

# Add corresponding CSS to projects.css
css_path = r"c:\Users\HP\PycharmProjects\Andd_baay\baay\static\css\projects.css"
new_css = """
/* ===== LIST PROJETS INLINE CLEANUP ===== */
.col-checkbox { width: 40px; }
.col-actions { width: 120px; }
.accent-checkbox { width: 18px; height: 18px; accent-color: var(--accent); }
.pointer { cursor: pointer; }
"""

with open(css_path, 'a', encoding='utf-8') as f:
    f.write(new_css)
    
print("Clean up completed successfully!")
