"""
Remplace les hex MARQUE/SÉMANTIQUES par les tokens --ab-color-* UNIQUEMENT dans
les attributs `style="..."` des templates (contexte CSS pur).

Sûr : n'opère que dans `style="..."` (jamais dans <script>/JS, où un hex Chart.js
ne doit pas devenir var()). Valeurs préservées à l'identique.

Usage : python scripts/migrate_inline_brand_hex.py [--apply]
"""
from __future__ import annotations

import glob
import os
import re
import sys

TPL_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")

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
_STYLE_ATTR = re.compile(r'style="([^"]*)"')


def _sub_in_value(value: str) -> tuple[str, int]:
    n = 0
    for hx, tok in HEX_MAP.items():
        pat = re.compile(re.escape(hx) + r"(?![0-9a-fA-F])", re.IGNORECASE)
        value, c = pat.subn(tok, value)
        n += c
    return value, n


def migrate_text(text: str) -> tuple[str, int]:
    counter = {"n": 0}

    def repl(m: re.Match) -> str:
        new_val, c = _sub_in_value(m.group(1))
        counter["n"] += c
        return f'style="{new_val}"'

    return _STYLE_ATTR.sub(repl, text), counter["n"]


def main() -> None:
    apply = "--apply" in sys.argv
    total = 0
    for path in sorted(glob.glob(os.path.join(TPL_DIR, "**", "*.html"), recursive=True)):
        with open(path, encoding="utf-8") as f:
            src = f.read()
        out, n = migrate_text(src)
        if n:
            total += n
            print(f"{os.path.relpath(path, TPL_DIR):50} {n:3d}")
            if apply:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(out)
    print(f"{'TOTAL':50} {total:3d}  ({'APPLIQUÉ' if apply else 'dry-run'})")


if __name__ == "__main__":
    main()
