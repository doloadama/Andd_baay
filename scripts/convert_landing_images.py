#!/usr/bin/env python
"""Convertit les images JPG de la landing en WebP (qualité 82)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
STATIC_IMAGES = ROOT / "baay" / "static" / "images"
TARGETS = ("hero-farmers.jpg", "og-cover.jpg")


def main() -> None:
    for name in TARGETS:
        src = STATIC_IMAGES / name
        if not src.exists():
            print(f"SKIP (missing): {name}")
            continue
        dst = src.with_suffix(".webp")
        img = Image.open(src)
        img.save(dst, "WEBP", quality=82, method=6)
        before = src.stat().st_size
        after = dst.stat().st_size
        pct = round((1 - after / before) * 100) if before else 0
        print(f"{name}: {before // 1024} KB -> {after // 1024} KB (-{pct}%)")


if __name__ == "__main__":
    main()
