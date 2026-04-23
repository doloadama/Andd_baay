import re

html_path = r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\dashboard.html"

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the tile-handle inline style
content = re.sub(r'<i class="fas fa-grip-vertical" style="font-size: 12px; color: var\(--text-muted\);"></i>', 
                 r'<i class="fas fa-grip-vertical"></i>', content)

# Replace the quick action block
quick_action_old = """<div style="width: 80px; height: 80px; background: rgba(163, 230, 53, 0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px auto;">
                <i class="fas fa-bolt fa-2x" style="color: var(--accent);"></i>
            </div>
            <h4 style="color: var(--text-main); font-family: var(--font-display); font-weight: 700; margin-bottom: 12px;">Nouveau Projet</h4>
            <p style="color: rgba(255,255,255,0.7); font-size: 0.9rem; margin-bottom: 24px;">Lancez une prédiction IA pour vos cultures.</p>"""

quick_action_new = """<div class="quick-action-icon-wrapper">
                <i class="fas fa-bolt fa-2x text-accent"></i>
            </div>
            <h4 class="quick-action-title">Nouveau Projet</h4>
            <p class="quick-action-desc">Lancez une prédiction IA pour vos cultures.</p>"""
            
content = content.replace(quick_action_old, quick_action_new)

# Replace active-filters display inline style
content = content.replace('<div class="active-filters" id="activeFilters" style="display: none;"></div>', 
                          '<div class="active-filters hidden" id="activeFilters"></div>')

# Replace inline style for dash-section-body padding 0
content = content.replace('<div class="dash-section-body" style="padding: 0;">', 
                          '<div class="dash-section-body p-0">')

# Replace inline style for progress bar
content = re.sub(r'<div class="project-progress-bar" style="width: {% if projet.statut == \'fini\' %}100{% elif projet.statut == \'en_pause\' %}50{% else %}75{% endif %}%"></div>',
                 r'<div class="project-progress-bar" style="width: {% if projet.statut == \'fini\' %}100{% elif projet.statut == \'en_pause\' %}50{% else %}75{% endif %}%"></div>', content) # actually this inline style is fine because it's dynamic

# Shortcuts panel inline close button padding
content = content.replace('<button class="modal-close" onclick="toggleShortcutsPanel()" style="padding: 2px;">&times;</button>',
                          '<button class="modal-close p-1" onclick="toggleShortcutsPanel()">&times;</button>')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

# Now let's add the new CSS classes to dashboard.css
css_path = r"c:\Users\HP\PycharmProjects\Andd_baay\baay\static\css\dashboard.css"

new_css = """
/* ===== NEW UTILITY CLASSES ADDED FOR REDESIGN ===== */
.dash-subtitle { margin-bottom: 4px; }
.filter-header-actions { display: flex; align-items: center; gap: 12px; }
.status-chart-container { height: 220px; }
.empty-state-padded { padding: 40px 20px; }
.action-delay { animation-delay: 0.4s; }
.quick-action-icon-wrapper { width: 80px; height: 80px; background: rgba(163, 230, 53, 0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px auto; }
.text-accent { color: var(--accent); }
.quick-action-title { color: var(--text-main); font-family: var(--font-display); font-weight: 700; margin-bottom: 12px; }
.quick-action-desc { color: rgba(255,255,255,0.7); font-size: 0.9rem; margin-bottom: 24px; }
.hidden { display: none !important; }
.p-0 { padding: 0 !important; }
.p-1 { padding: 2px !important; }

/* Handle specific tile styles */
.tile-handle i { font-size: 12px; color: var(--text-muted); }
"""

with open(css_path, 'a', encoding='utf-8') as f:
    f.write(new_css)
    
print("Clean up completed successfully!")
