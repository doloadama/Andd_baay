filepath = r"c:\Users\HP\PycharmProjects\Andd_baay\templates\base.html"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_css = """
        /* ===== GLOBAL BACKGROUND WITH GRAIN (Requested Design) ===== */
        .background-container {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100vh;
            z-index: -10;
            background-color: #0d1117; /* Fond sombre de base */
            background-image: 
                /* Lueurs vertes diffuses (Cercles radiaux) */
                radial-gradient(circle at 10% 20%, rgba(144, 238, 144, 0.05) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(46, 139, 87, 0.08) 0%, transparent 40%),
                /* Dégradé linéaire pour la profondeur */
                linear-gradient(135deg, #0d1117 0%, #161b22 100%);
        }

        /* Effet de grain pour le côté "Premium" */
        .background-container::before {
            content: "";
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            opacity: 0.02;
            pointer-events: none;
            background-image: url("https://grainy-gradients.vercel.app/noise.svg");
        }
"""

if "</style>" in content and ".background-container {" not in content:
    content = content.replace("</style>", new_css + "    </style>")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Added .background-container CSS block")
elif ".background-container {" in content:
    print("WARNING: CSS block already exists")
else:
    print("ERROR: Could not find </style> tag")
