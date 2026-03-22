import os
import re

files_to_fix = [
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\modifier_projet.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\creer_projet.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\detail_projet.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\ajouter_investissement.html"
]

for filepath in files_to_fix:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        
        # We replace specific text-white and text-dark classes ensuring no clash with dynamic themes
        content = re.sub(r'\btext-white-50\b', 'text-muted', content)
        content = re.sub(r'\btext-white\b', '', content)
        content = re.sub(r'\btext-dark\b', '', content)
        content = re.sub(r'\btext-black\b', '', content)
        
        # Fix any remaining style="... color: white;" inside these specific elements 
        # (Though we largely fixed it in the previous script)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Cleaned up hardcoded text classes in {os.path.basename(filepath)}")

print("Text color verification and fix complete.")
