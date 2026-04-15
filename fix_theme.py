import os
import re

files_to_fix = [
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\modifier_projet.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\creer_projet.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\detail_projet.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\liste_projets.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\ajouter_investissement.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\dashboard.html",
]

replacements = [
    # Backgrounds
    ("background: linear-gradient(135deg, #020617 0%, #022c22 50%, #0f172a 100%);", "background: linear-gradient(135deg, var(--bg-main) 0%, var(--bg-secondary) 100%);"),
    ("background: linear-gradient(135deg, #020617 0%, #022c22 100%);", "background: linear-gradient(135deg, var(--bg-main) 0%, var(--bg-secondary) 100%);"),
    ("background: rgba(15, 23, 42, 0.75);", "background: var(--card-bg);"),
    ("background: linear-gradient(135deg, rgba(2, 44, 34, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);", "background: var(--card-bg-solid);"),
    ("background: rgba(255, 255, 255, 0.03);", "background: var(--bg-secondary);"),
    ("background: rgba(163, 230, 53, 0.05);", "background: var(--bg-main);"),
    ("background: #0f172a;", "background: var(--card-bg-solid);"),
    ("background: rgba(255, 255, 255, 0.05);", "background: var(--bg-secondary);"),
    ("background: rgba(255, 255, 255, 0.08);", "background: var(--bg-main);"),
    
    # Borders
    ("border: 1px solid rgba(163, 230, 53, 0.15);", "border: 1px solid var(--border-color);"),
    ("border-bottom: 1px solid rgba(163, 230, 53, 0.2);", "border-bottom: 1px solid var(--border-color);"),
    ("border: 2px solid rgba(255, 255, 255, 0.1);", "border: 2px solid var(--border-color);"),
    
    # Text colors that break light mode
    ("color: white;", "color: var(--text-main);"),
    ("color: white !important;", "color: var(--text-main) !important;"),
    ("color: rgba(255, 255, 255, 0.9);", "color: var(--text-main);"),
    ("color: rgba(255, 255, 255, 0.4);", "color: var(--text-muted);"),
]

for filepath in files_to_fix:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        
        # Apply specific replacements
        for old, new in replacements:
            content = content.replace(old, new)
            
        # Revert 'color: var(--text-main);' for elements that specifically need to remain white
        # like buttons or badges that have accent/success/danger backgrounds.
        # Use regex to find `background: var(--danger); color: var(--text-main);` and swap back to white.
        content = re.sub(r'(background:\s*var\(--danger\);\s*color:\s*)var\(--text-main\);', r'\1white;', content)
        content = re.sub(r'(background:\s*var\(--success\);\s*color:\s*)var\(--text-main\);', r'\1white;', content)
        content = re.sub(r'class="text-white-50"', 'class="text-muted"', content)
        content = re.sub(r'class="text-white"', 'class="text-body"', content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {os.path.basename(filepath)}")

print("Theme modifications applied.")
