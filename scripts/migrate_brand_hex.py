"""
Migration sûre : remplace les littéraux de couleur MARQUE/SÉMANTIQUES par les
tokens canoniques `--ab-color-*` dans les fichiers CSS (hors tokens.css).

Sûr par construction : chaque remplacement préserve la valeur exacte (un hex de
marque → le token qui vaut ce même hex). N'agit que sur les CSS (jamais les
templates, où un hex peut vivre dans du JS/Chart.js et casserait).

Usage : python scripts/migrate_brand_hex.py [--apply]
Sans --apply : dry-run (compte seulement).
"""
from __future__ import annotations

import glob
import os
import re
import sys

CSS_DIR = os.path.join(os.path.dirname(__file__), "..", "baay", "static", "css")

# hex exact (insensible casse) -> token (même valeur)
HEX_MAP = {
    "#1d9e75": "var(--ab-color-primary)",
    "#157a5a": "var(--ab-color-primary-dark)",
    "#085041": "var(--ab-color-primary-deep)",
    "#04342c": "var(--ab-color-primary-night)",
    "#16856a": "var(--ab-color-primary-mid)",
    "#ef9f27": "var(--ab-color-accent)",
    "#16a34a": "var(--ab-color-success)",
    "#dc2626": "var(--ab-color-danger)",
    "#b91c1c": "var(--ab-color-depense)",
    "#d97706": "var(--ab-color-warning)",
    "#78350f": "var(--ab-color-terre)",
}
# rgba(29,158,117, A) -> rgba(var(--ab-color-primary-rgb), A)  (valeur identique)
RGBA_PRIMARY = re.compile(r"rgba\(\s*29\s*,\s*158\s*,\s*117\s*,", re.IGNORECASE)


def migrate_text(text: str) -> tuple[str, int]:
    n = 0
    for hx, tok in HEX_MAP.items():
        # match le hex exact suivi d'une frontière (pas un hex plus long)
        pat = re.compile(re.escape(hx) + r"(?![0-9a-fA-F])", re.IGNORECASE)
        text, c = pat.subn(tok, text)
        n += c
    text, c = RGBA_PRIMARY.subn("rgba(var(--ab-color-primary-rgb),", text)
    n += c
    return text, n


def main() -> None:
    apply = "--apply" in sys.argv
    total = 0
    for path in sorted(glob.glob(os.path.join(CSS_DIR, "*.css"))):
        if os.path.basename(path) == "tokens.css":
            continue
        with open(path, encoding="utf-8") as f:
            src = f.read()
        out, n = migrate_text(src)
        if n:
            total += n
            print(f"{os.path.basename(path):32} {n:4d}")
            if apply:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(out)
    print(f"{'TOTAL':32} {total:4d}  ({'APPLIQUÉ' if apply else 'dry-run'})")


if __name__ == "__main__":
    main()
