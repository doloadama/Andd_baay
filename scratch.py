import os

file_path = "c:\\Users\\HP\\PycharmProjects\\Andd_baay\\templates\\projets\\dashboard.html"
css_path = "c:\\Users\\HP\\PycharmProjects\\Andd_baay\\baay\\static\\css\\dashboard.css"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

css_lines = []
in_style = False
style_start = -1
style_end = -1

for i, line in enumerate(lines):
    if "<style>" in line and not in_style:
        in_style = True
        style_start = i
    elif "</style>" in line and in_style:
        style_end = i
        break
    elif in_style:
        css_lines.append(line)

if style_start != -1 and style_end != -1:
    with open(css_path, "w", encoding="utf-8") as f:
        f.writelines(css_lines)
    
    new_lines = lines[:style_start] + ['<link rel="stylesheet" href="{% static \'css/dashboard.css\' %}">\n'] + lines[style_end+1:]
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("CSS extracted successfully")
else:
    print("Could not find style block")
