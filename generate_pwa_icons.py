#!/usr/bin/env python3
"""Generate square PWA icon placeholders for Andd Baay."""
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow is not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
    from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).parent / "baay" / "static" / "icons"
OUT_DIR.mkdir(parents=True, exist_ok=True)

THEME_BG = (15, 23, 42)      # #0f172a
ACCENT = (163, 230, 53)       # #a3e635
WHITE = (248, 250, 252)
SIZES = [192, 512]

def draw_leaf(draw, cx, cy, size, color):
    """Draw a simple stylized leaf."""
    s = size
    # Main leaf shape (ellipse rotated)
    draw.ellipse([cx - s//3, cy - s//2, cx + s//3, cy + s//2], fill=color)
    # Stem
    draw.polygon([
        (cx, cy + s//2),
        (cx - s//12, cy + s//2 + s//3),
        (cx + s//12, cy + s//2 + s//3),
    ], fill=color)

def generate_icon(px):
    img = Image.new("RGBA", (px, px), THEME_BG)
    draw = ImageDraw.Draw(img)

    # Background circle glow
    glow_radius = int(px * 0.42)
    glow_center = px // 2
    for r in range(glow_radius, 0, -2):
        alpha = int(20 * (1 - r / glow_radius))
        draw.ellipse(
            [glow_center - r, glow_center - r, glow_center + r, glow_center + r],
            fill=(*ACCENT, alpha),
        )

    # Draw leaf symbol
    leaf_size = int(px * 0.28)
    draw_leaf(draw, glow_center, glow_center - leaf_size // 6, leaf_size, ACCENT)

    # Add text "AB" if large enough
    if px >= 512:
        try:
            font = ImageFont.truetype("arial.ttf", int(px * 0.12))
        except Exception:
            font = ImageFont.load_default()
        text = "Andd Baay"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (px - tw) // 2
        ty = px - int(px * 0.12) - th
        draw.text((tx, ty), text, font=font, fill=WHITE)

    return img

for size in SIZES:
    icon = generate_icon(size)
    out_path = OUT_DIR / f"icon-{size}x{size}.png"
    icon.save(out_path, "PNG")
    print(f"Generated {out_path}")

print("Done. Update manifest.json to point to /static/icons/icon-192x192.png and /static/icons/icon-512x512.png")
