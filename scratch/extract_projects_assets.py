import os

html_path = r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\liste_projets.html"
css_path = r"c:\Users\HP\PycharmProjects\Andd_baay\baay\static\css\projects.css"
js_path = r"c:\Users\HP\PycharmProjects\Andd_baay\baay\static\js\projects.js"

with open(html_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Extract Style
style_start = -1
style_end = -1
script_start = -1
script_end = -1

for i, line in enumerate(lines):
    if '<style>' in line and style_start == -1:
        style_start = i
    elif '</style>' in line and style_start != -1 and style_end == -1:
        style_end = i
    elif '<script>' in line and script_start == -1:
        script_start = i
    elif '</script>' in line and script_start != -1 and script_end == -1:
        script_end = i

if style_start != -1 and style_end != -1:
    css_content = "".join(lines[style_start+1:style_end])
    # Append to existing projects.css
    with open(css_path, 'a', encoding='utf-8') as f:
        f.write("\n/* Extracted from liste_projets.html */\n")
        f.write(css_content)

if script_start != -1 and script_end != -1:
    js_content = "".join(lines[script_start+1:script_end])
    os.makedirs(os.path.dirname(js_path), exist_ok=True)
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_content)

# Rebuild HTML
new_html = []
i = 0
while i < len(lines):
    if i == style_start:
        new_html.append('<link rel="stylesheet" href="{% static \'css/projects.css\' %}">\n')
        i = style_end + 1
    elif i == script_start:
        new_html.append('<script src="{% static \'js/projects.js\' %}"></script>\n')
        i = script_end + 1
    else:
        new_html.append(lines[i])
        i += 1

with open(html_path, 'w', encoding='utf-8') as f:
    f.writelines(new_html)

print(f"Extracted {style_end - style_start - 1} lines of CSS.")
print(f"Extracted {script_end - script_start - 1} lines of JS.")
