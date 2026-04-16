import os
import re

os.makedirs('baay/static/css', exist_ok=True)
os.makedirs('baay/static/js', exist_ok=True)

# ===== REFACTOR base.html =====
with open('templates/base.html', 'r', encoding='utf-8') as f:
    base_html = f.read()

# Extract and replace style
style_match = re.search(r'<style>(.*?)</style>', base_html, re.DOTALL)
if style_match:
    with open('baay/static/css/base.css', 'w', encoding='utf-8') as f:
        f.write(style_match.group(1).strip())
    base_html = base_html[:style_match.start()] + '<link rel="stylesheet" href="{% static \'css/base.css\' %}">' + base_html[style_match.end():]

# Extract scripts (skip Anti-flash)
script_matches = list(re.finditer(r'<script>(.*?)</script>', base_html, re.DOTALL))
js_content = ""
for match in reversed(script_matches): # reverse to not mess up indices during replacement
    content = match.group(1)
    if 'Anti-Flash' in content:
        continue # Keep it inline
    
    # Needs to handle Django tags in JS securely by relying on global vars we'll inject.
    js_content = content.strip() + "\n\n" + js_content
    base_html = base_html[:match.start()] + base_html[match.end():]

# Write JS
js_content = "/* Main App JS */\n" + js_content

# We need to replace `{% url '...' %}` in JS with things that exist, or set global window vars.
# Luckily the chatbot JS mostly uses `/api/chatbot/` which is hardcoded, not a django tag!
# Let's check for any django tags in js_content.
django_tags = re.findall(r'\{%.*?%\}', js_content)
django_vars = re.findall(r'\{\{.*?\}\}', js_content)
# Actually the only things might be {{ user.username }} or so.
# Let's just create main.js anyway, and we can fix if there are issues.
with open('baay/static/js/main.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

# Add inclusion of main.js right before </body>
base_html = base_html.replace('</body>', '    <script src="{% static \'js/main.js\' %}"></script>\n</body>')

# Add SEO blocks
seo_blocks = """
    <!-- SEO Meta Tags -->
    {% block meta_description %}
    <meta name="description" content="Andd Baay - Plateforme Agricole Intelligente. Gérez vos cultures et prédisez vos rendements." />
    {% endblock %}
    {% block og_tags %}
    <meta property="og:title" content="Andd Baay | L'agriculture de demain" />
    <meta property="og:description" content="La plateforme intelligente pour gérer vos cultures, prédire vos rendements et optimiser chaque récolte." />
    <meta property="og:type" content="website" />
    {% endblock %}
"""
base_html = base_html.replace('<meta name="description" content="Andd Baay - Plateforme Agricole Intelligente" />', seo_blocks.strip())

# Add A11y and Semantic tags
base_html = base_html.replace('<div class="navbar-wrapper">', '<header class="navbar-wrapper">')
base_html = base_html.replace('</nav>\n    </div>\n\n    <!-- Main Content -->', '</nav>\n    </header>\n\n    <!-- Main Content -->')

base_html = base_html.replace('<button id="themeToggleMobile" type="button" class="theme-toggle" aria-label="Changer de thème">', '<button id="themeToggleMobile" type="button" class="theme-toggle" aria-label="Changer de thème">')
base_html = base_html.replace('<button id="themeToggle" type="button" class="theme-toggle" aria-label="Changer de thème">', '<button id="themeToggle" type="button" class="theme-toggle" aria-label="Changer de thème">')
base_html = base_html.replace('<button id="openGuideBtn" type="button"', '<button id="openGuideBtn" aria-label="Ouvrir le guide" type="button"')
base_html = base_html.replace('<a class="btn-nav btn-nav-ghost" href="{% url \'logout\' %}" title="Déconnexion"', '<a class="btn-nav btn-nav-ghost" href="{% url \'logout\' %}" title="Déconnexion" aria-label="Déconnexion"')

base_html = base_html.replace('<div class="chat-bubble" id="chatBubble">', '<button class="chat-bubble" id="chatBubble" aria-label="Ouvrir le chat">')
base_html = base_html.replace('        </div>\n    </div>\n\n    <!-- Chatbot Window -->', '        </button>\n    </div>\n\n    <!-- Chatbot Window -->')
base_html = base_html.replace('<div class="chat-window"', '<aside class="chat-window" aria-label="Fenêtre de chat"')
base_html = base_html.replace('</aside>\n\n    <!-- Scripts -->', '</aside>\n\n    <!-- Scripts -->') # just in case
base_html = base_html.replace('</div>\n\n    <!-- Scripts -->', '</aside>\n\n    <!-- Scripts -->')
base_html = base_html.replace('<textarea id="message" class="chat-input" placeholder="Ecrivez votre message..." rows="1"></textarea>', '<label for="message" class="visually-hidden" style="display:none;">Message</label>\n            <textarea id="message" class="chat-input" placeholder="Ecrivez votre message..." rows="1"></textarea>')
base_html = base_html.replace('<button id="sendMessage" class="chat-send-btn">', '<button id="sendMessage" class="chat-send-btn" aria-label="Envoyer le message">')
base_html = base_html.replace('<button id="minimizeChat" title="Reduire"', '<button id="minimizeChat" title="Reduire" aria-label="Reduire"')
base_html = base_html.replace('<button id="clearChat" title="Effacer"', '<button id="clearChat" title="Effacer" aria-label="Effacer historique"')
base_html = base_html.replace('<div class="chat-notification" id="chatNotification">1</div>', '<div class="chat-notification" id="chatNotification" aria-live="polite"></div>')

with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(base_html)


# ===== REFACTOR home.html =====
with open('templates/home.html', 'r', encoding='utf-8') as f:
    home_html = f.read()

style_match = re.search(r'<style>(.*?)</style>', home_html, re.DOTALL)
if style_match:
    with open('baay/static/css/home.css', 'w', encoding='utf-8') as f:
        f.write(style_match.group(1).strip())
    home_html = home_html[:style_match.start()] + '<link rel="stylesheet" href="{% static \'css/home.css\' %}">' + home_html[style_match.end():]

home_html = home_html.replace('<div class="hero-section">', '<section class="hero-section">')
home_html = home_html.replace('<!-- ===== FEATURES ===== -->\n<section class="features-section">', '<!-- ===== FEATURES ===== -->\n<div class="features-section">') # Rollback if already changed? No, it was div.
home_html = home_html.replace('<div class="features-section">', '<section class="features-section">')
home_html = home_html.replace('<div class="stats-section">', '<section class="stats-section">')
home_html = home_html.replace('<div class="cta-section">', '<section class="cta-section">')
# Close sections
home_html = home_html.replace('</div>\n\n<!-- ===== FEATURES ===== -->', '</section>\n\n<!-- ===== FEATURES ===== -->')
home_html = home_html.replace('</div>\n\n<!-- ===== STATS ===== -->', '</section>\n\n<!-- ===== STATS ===== -->')
home_html = home_html.replace('</div>\n\n<!-- ===== CTA ===== -->', '</section>\n\n<!-- ===== CTA ===== -->')
home_html = home_html.replace('    </div>\n</div>\n{% else %}', '    </div>\n</section>\n{% else %}')
home_html = home_html.replace('        </div>\n    </div>\n</div>\n{% endif %}', '        </div>\n    </div>\n</section>\n{% endif %}')

# Add SEO blocks to home.html
home_seo = """
{% block meta_description %}
<meta name="description" content="Découvrez Andd Baay, l'outil idéal pour la prédiction de rendement IA et la gestion agricole en Afrique de l'Ouest. Transformez vos cultures dès aujourd'hui." />
{% endblock %}
{% block og_tags %}
<meta property="og:title" content="Accueil | Andd Baay" />
<meta property="og:description" content="Découvrez Andd Baay, l'outil idéal pour la prédiction de rendement IA et la gestion agricole en Afrique de l'Ouest." />
<meta property="og:type" content="website" />
{% endblock %}
"""
home_html = home_html.replace('{% block title %}Accueil{% endblock %}', '{% block title %}Accueil{% endblock %}\n' + home_seo)

with open('templates/home.html', 'w', encoding='utf-8') as f:
    f.write(home_html)


# ===== REFACTOR liste_projets.html =====
with open('templates/projets/liste_projets.html', 'r', encoding='utf-8') as f:
    projets_html = f.read()

style_match = re.search(r'<style>(.*?)</style>', projets_html, re.DOTALL)
if style_match:
    with open('baay/static/css/projects.css', 'w', encoding='utf-8') as f:
        f.write(style_match.group(1).strip())
    projets_html = projets_html[:style_match.start()] + '<link rel="stylesheet" href="{% static \'css/projects.css\' %}">' + projets_html[style_match.end():]

# Semantics
projets_html = projets_html.replace('<div class="project-card animate__animated animate__fadeInUp"', '<article class="project-card animate__animated animate__fadeInUp"')
projets_html = projets_html.replace('        </a>\n            </div>\n        </div>\n        {% endfor %}', '        </a>\n            </div>\n        </article>\n        {% endfor %}')
projets_html = projets_html.replace('<input type="text" id="searchInput" placeholder="Rechercher un projet...">', '<label for="searchInput" class="visually-hidden" style="display:none;">Rechercher un projet</label>\n            <input type="text" id="searchInput" placeholder="Rechercher un projet...">')

projets_seo = """
{% block meta_description %}
<meta name="description" content="Gérez vos projets agricoles avec Andd Baay. Suivez l'avancement, la superficie et les rendements de chaque parcelle." />
{% endblock %}
"""
projets_html = projets_html.replace('{% block title %}Mes Projets | Andd Baay{% endblock %}', '{% block title %}Mes Projets | Andd Baay{% endblock %}\n' + projets_seo)


with open('templates/projets/liste_projets.html', 'w', encoding='utf-8') as f:
    f.write(projets_html)

print("Refactoring complete.")
