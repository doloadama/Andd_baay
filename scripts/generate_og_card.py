"""
Génère la carte sociale Open Graph 1200x630 d'Andd Baay.

Sortie : baay/static/images/og-card.png (référencée par og:image / twitter:image
dans templates/base.html).

Usage : python scripts/generate_og_card.py
Reproductible : palette de la landing (.ab-land). Police Arial (Windows) avec
repli DejaVu. L'image générée est committée — pas regénérée en prod.
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
OUT = os.path.join(os.path.dirname(__file__), "..", "baay", "static", "images", "og-card.png")

# Palette Andd Baay (cf. home.html .ab-land)
NIGHT = (4, 36, 29)      # #04241d
DEEP = (8, 80, 65)       # #085041
BRAND = (29, 158, 117)   # #1D9E75
PALE = (159, 225, 203)   # #9FE1CB
ACCENT = (239, 159, 39)  # #EF9F27
WHITE = (255, 255, 255)


def _font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _bold(size: int) -> ImageFont.FreeTypeFont:
    return _font([
        r"C:\Windows\Fonts\arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ], size)


def _reg(size: int) -> ImageFont.FreeTypeFont:
    return _font([
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ], size)


def _lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def main() -> None:
    img = Image.new("RGB", (W, H), NIGHT)
    px = img.load()
    # Dégradé diagonal NIGHT -> DEEP -> BRAND.
    for y in range(H):
        for x in range(W):
            t = (x / W + y / H) / 2
            c = _lerp(NIGHT, DEEP, t * 2) if t < 0.5 else _lerp(DEEP, BRAND, (t - 0.5) * 2)
            px[x, y] = c

    draw = ImageDraw.Draw(img)

    # Pastille texture en haut à droite (cohérence landing).
    draw.ellipse([W - 280, -160, W + 120, 240], fill=_lerp(BRAND, WHITE, 0.06))

    pad = 90
    # Eyebrow.
    draw.ellipse([pad, 150, pad + 16, 166], fill=ACCENT)
    draw.text((pad + 30, 146), "AGRICULTURE INTELLIGENTE DU SAHEL",
              font=_bold(26), fill=PALE)

    # Wordmark.
    draw.text((pad, 210), "Andd Baay", font=_bold(132), fill=WHITE)

    # Tagline (2 lignes).
    draw.text((pad, 372), "Prédiction de rendement, assistant vocal Wolof,",
              font=_reg(40), fill=PALE)
    draw.text((pad, 424), "prix du marché — même hors connexion.",
              font=_reg(40), fill=PALE)

    # Filet accent + URL.
    draw.rectangle([pad, 520, pad + 90, 526], fill=ACCENT)
    draw.text((pad, 548), "anddbaay.sn", font=_bold(30), fill=WHITE)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"OK -> {os.path.normpath(OUT)} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
