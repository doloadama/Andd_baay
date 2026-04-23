import os
import re

files_to_fix = [
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\auth\login.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\auth\register.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\auth\profil.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\home.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\detail_projet.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\dashboard.html",
]

replacements = [
    ("background: linear-gradient(160deg, #022c22 0%, #030712 60%, #0f172a 100%);", "background: linear-gradient(160deg, var(--primary) 0%, var(--bg-main) 60%, var(--bg-secondary) 100%);"),
    ("background: linear-gradient(135deg, rgba(2, 44, 34, 0.9) 0%, rgba(2, 6, 23, 0.95) 100%);", "background: linear-gradient(135deg, var(--bg-main) 0%, var(--bg-secondary) 100%);"),
    ("background: linear-gradient(135deg, rgba(2, 44, 34, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%);", "background: linear-gradient(135deg, var(--bg-main) 0%, var(--bg-secondary) 100%);"),
    ("background: linear-gradient(135deg, #022c22 0%, #064e3b 100%);", "background: var(--primary-light);"),
]

for filepath in files_to_fix:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        
        for old, new in replacements:
            content = content.replace(old, new)
            
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {os.path.basename(filepath)}")

print("More theme modifications applied.")
