"""
Génère les PNG favicon / PWA à partir du design vectoriel (équivalent au SVG mark).
Exécuter depuis la racine du projet : python scripts/generate_anddbaay_icons.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "baay" / "static" / "icons"


def draw_mark(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(1, round(size * 0.0625))
    r = max(2, round(size * 0.21875))
    # Fond arrondi
    d.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=r,
        fill=(34, 197, 94, 255),
    )
    cx = size // 2
    # Forme « épi » (approximation ellipse + clip visuelle)
    ew, eh = round(size * 0.28), round(size * 0.42)
    ey = round(size * 0.36)
    d.ellipse(
        [cx - ew, ey - eh, cx + ew, ey + eh],
        fill=(20, 83, 45, 255),
    )
    ew2, eh2 = round(size * 0.14), round(size * 0.22)
    ey2 = round(size * 0.38)
    d.ellipse(
        [cx - ew2, ey2 - eh2, cx + ew2, ey2 + eh2],
        fill=(240, 253, 244, 235),
    )
    # Lignes fines type « donnée »
    lw = max(1, round(size / 64))
    y1, y2 = round(size * 0.37), round(size * 0.6)
    d.line([cx, y1, cx, y2], fill=(187, 247, 208, 140), width=lw)
    xw = round(size * 0.1)
    d.line([cx - xw, round(size * 0.47), cx + xw, round(size * 0.47)], fill=(187, 247, 208, 140), width=lw)
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = [
        (32, "favicon-32x32.png"),
        (180, "apple-touch-icon-180x180.png"),
        (192, "icon-192x192.png"),
        (512, "icon-512x512.png"),
    ]
    for dim, name in targets:
        im = draw_mark(dim)
        path = OUT_DIR / name
        im.save(path, format="PNG", optimize=True)
        print(f"Wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
