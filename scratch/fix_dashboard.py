import os, re
path = 'templates/projets/dashboard.html'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Extract inline <style>...</style>
style_match = re.search(r'<style>(.*?)</style>', text, re.DOTALL)
if style_match:
    css_content = style_match.group(1).strip()
    
    css_path = 'baay/static/css/dashboard.css'
    with open(css_path, 'w', encoding='utf-8') as cf:
        cf.write(css_content)

    replacement = '<link rel="stylesheet" href="{% static \'css/dashboard.css\' %}">'
    
    # Check if load static is present
    if '{% load static %}' not in text:
        text = text.replace('{% extends \'base.html\' %}', '{% extends \'base.html\' %}\n{% load static %}')

    text = text[:style_match.start()] + replacement + text[style_match.end():]
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print('Successfully clean dashboard inline styles!')
else:
    print('No inline style found.')
