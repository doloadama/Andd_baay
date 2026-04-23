import re

filepath = r"c:\Users\HP\PycharmProjects\Andd_baay\templates\base.html"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the theme initialization logic
old = """            // Check saved theme or system preference
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'dark' || (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                body.classList.add('dark-mode');
            }"""

new = """            // Check saved theme — dark mode is default
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme !== 'light') {
                body.classList.add('dark-mode');
            }"""

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Dark mode is now the default!")
else:
    print("ERROR: Could not find the target code block")
    # Debug: show what's around line 1302
    lines = content.split('\n')
    for i in range(1298, 1310):
        print(f"Line {i+1}: {repr(lines[i])}")
