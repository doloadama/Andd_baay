from pathlib import Path
import re

base = Path('templates/base.html')
text = base.read_text(encoding='utf-8')

# Replace inline CSS block in head with external stylesheet reference
pattern = re.compile(
    r'(<link href="https://cdn.jsdelivr.net/npm/bootstrap@5\.3\.0/dist/css/bootstrap.min\.css" rel="stylesheet" />\n    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6\.4\.0/css/all\.min\.css" rel="stylesheet" />\n    <link href="https://cdnjs.cloudflare.com/ajax/libs/animate\.css/4\.1\.1/animate\.min\.css" rel="stylesheet" />\n\n    <!-- Leaflet : charge conditionnellement par chaque template qui en a besoin -->\n    \{% block extra_head %\}{% endblock %}\n\n)    <style>.*?</style>\n    <script>',
    re.S,
)
text, n = pattern.subn(
    r"\1    <link rel=\"stylesheet\" href=\"{% static 'css/base.css' %}\" />\n    <script>",
    text,
)
if n != 1:
    raise RuntimeError(f'CSS block replacement failed: {n} matches')

# Replace inline theme-init script block in head
pattern = re.compile(r'    <script>\n        // Anti-Flash : Applique le thème avant le rendu du body.*?</script>\n</head>', re.S)
text, n = pattern.subn(r'    <script src="{% static \'js/theme-init.js\' %}"></script>\n</head>', text)
if n != 1:
    raise RuntimeError(f'theme-init block replacement failed: {n} matches')

# Replace bottom inline base JS block before onboarding script
pattern = re.compile(
    r'<script src="https://cdn.jsdelivr.net/npm/bootstrap@5\.3\.0/dist/js/bootstrap.bundle.min\.js"></script>\n    <script>.*?</script>\n\n    <!-- ===== ONBOARDING TOUR SCRIPT ===== -->',
    re.S,
)
text, n = pattern.subn(
    r'<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>\n    <script src="{% static \'js/base.js\' %}"></script>\n\n    <!-- ===== ONBOARDING TOUR SCRIPT ===== -->',
    text,
)
if n != 1:
    raise RuntimeError(f'Bottom JS replacement failed: {n} matches')

# Add meta_tags and title blocks if missing
if '<title>{% block title %}' not in text:
    text = text.replace(
        '<meta name="description" content="Andd Baay - Plateforme Agricole Intelligente" />\n    <meta name="theme-color" content="#a3e635" />\n\n    <title>Andd Baay | L\'agriculture de demain</title>',
        '<meta name="description" content="Andd Baay - Plateforme Agricole Intelligente" />\n    {% block meta_tags %}{% endblock %}\n    <meta name="theme-color" content="#a3e635" />\n\n    <title>{% block title %}Andd Baay | L\'agriculture de demain{% endblock %}</title>'
    )

# Improve chat accessibility
text = text.replace(
    '<div class="chat-bubble" id="chatBubble">',
    '<div class="chat-bubble" id="chatBubble" role="button" aria-label="Ouvrir le chat">',
)
text = text.replace(
    '<div class="chat-notification" id="chatNotification">1</div>',
    '<div class="chat-notification" id="chatNotification" aria-live="polite" aria-atomic="true" hidden></div>',
)
text = text.replace(
    '<button id="clearChat" title="Effacer"><i class="fas fa-trash-alt"></i></button>',
    '<button id="clearChat" title="Effacer" aria-label="Effacer le chat"><i class="fas fa-trash-alt" aria-hidden="true"></i></button>',
)
text = text.replace(
    '<button id="minimizeChat" title="Reduire"><i class="fas fa-chevron-down"></i></button>',
    '<button id="minimizeChat" title="Réduire" aria-label="Réduire le chat"><i class="fas fa-chevron-down" aria-hidden="true"></i></button>',
)
text = text.replace(
    '<div class="chat-input-container">\n            <textarea id="message" class="chat-input" placeholder="Ecrivez votre message..." rows="1"></textarea>\n            <button id="sendMessage" class="chat-send-btn">',
    '<div class="chat-input-container">\n            <label for="message" class="visually-hidden">Écrire un message</label>\n            <textarea id="message" class="chat-input" placeholder="Écrivez votre message..." rows="1"></textarea>\n            <button id="sendMessage" class="chat-send-btn" aria-label="Envoyer le message">',
)
text = text.replace(
    '<div id="chat-messages" class="chat-messages">',
    '<div id="chat-messages" class="chat-messages" role="log" aria-live="polite" aria-relevant="additions">',
)

base.write_text(text, encoding='utf-8')
print('base.html updated successfully')
