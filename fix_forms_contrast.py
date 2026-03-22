import os
import re

files_to_fix = [
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\creer_projet.html",
    r"c:\Users\HP\PycharmProjects\Andd_baay\templates\projets\modifier_projet.html"
]

replacements = [
    # Progress Top Bar
    ("background: rgba(0, 0, 0, 0.2);", "background: var(--bg-secondary); border-bottom: 1px solid var(--border-color);"),
    
    # Progress Steps
    ("background: rgba(255, 255, 255, 0.1);", "background: var(--bg-main);"),
    ("border: 2px solid rgba(255, 255, 255, 0.2);", "border: 2px solid var(--border-color);"),
    ("color: rgba(255, 255, 255, 0.5);", "color: var(--text-muted);"),
    
    # Connectors
    (".step-connector {\n        width: 40px;\n        height: 2px;\n        background: rgba(255, 255, 255, 0.1);", 
     ".step-connector {\n        width: 40px;\n        height: 2px;\n        background: var(--border-color);"),
     
    # Info Card Text
    ("color: rgba(255, 255, 255, 0.6);", "color: var(--text-muted);"),
    
    # Inputs placeholders
    ("color: rgba(255, 255, 255, 0.3);", "color: var(--text-muted); opacity: 0.6;"),
    
    # Back button
    ("border: 2px solid rgba(255, 255, 255, 0.15);", "border: 2px solid var(--border-color);"),
    ("color: rgba(255, 255, 255, 0.7);", "color: var(--text-muted);"),
]

for filepath in files_to_fix:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        
        for old, new in replacements:
            content = content.replace(old, new)
            
        # Revert any bad replacements if they match unexpectedly
        # (Using strict replacement values above prevents most)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed contrast in {os.path.basename(filepath)}")

print("Form contrast fixes applied.")
