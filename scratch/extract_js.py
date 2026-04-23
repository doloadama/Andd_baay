import os

html_path = r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\dashboard.html"
js_path = r"c:\Users\HP\PycharmProjects\Andd_baay\baay\static\js\dashboard.js"

with open(html_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if '<script>' in line and start_idx == -1:
        # Check if it's the large script block
        if '// ===== GLOBAL DATA STORE =====' in lines[i+1]:
            start_idx = i
    if '</script>' in line and start_idx != -1:
        end_idx = i

if start_idx != -1 and end_idx != -1:
    js_content = "".join(lines[start_idx+1:end_idx])
    
    # Save the JS file
    os.makedirs(os.path.dirname(js_path), exist_ok=True)
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_content)
        
    # Create the new HTML content
    new_html_content = "".join(lines[:start_idx]) + "<!-- Dashboard Logic -->\n<script src=\"{% static 'js/dashboard.js' %}\"></script>\n" + "".join(lines[end_idx+1:])
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_html_content)
        
    print(f"Successfully extracted {end_idx - start_idx - 1} lines of JS to {js_path}")
else:
    print("Could not find script block")
