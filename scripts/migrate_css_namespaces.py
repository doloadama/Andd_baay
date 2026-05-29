#!/usr/bin/env python3
"""
Migration des custom properties CSS legacy vers le prefixe canonique --ab-*.

Usage:
  python scripts/migrate_css_namespaces.py --dry-run   # rapport sans ecriture
  python scripts/migrate_css_namespaces.py --apply     # applique + backup .bak

Scanne baay/static/css/**.css ET les templates (style= inline + <style>).
Les prefixes VENDOR (--tw-, --bs-, --fa-) sont preserves : ce sont des
variables runtime des librairies, les renommer casse l'application.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Prefixes VENDOR a NE JAMAIS toucher (variables runtime des libs).
VENDOR_PREFIXES = ("--tw-", "--bs-", "--fa-")

# Prefixes/tokens legacy -> migres vers --ab-*.
LEGACY_PREFIXES = [
    "--pd-", "--pc-", "--invl-", "--inv-", "--fl-", "--at-",
    "--persona-", "--tech-", "--neon-", "--safran-", "--rain-",
    "--snow-", "--cloud-", "--msg-", "--fd-",
    # tokens non-prefixes a canoniser :
    "--text-", "--radius-", "--border-", "--brand-", "--bg-",
    "--card-", "--space-", "--font-", "--accent-", "--shadow-", "--green-",
]

TARGETS = list((ROOT / "baay" / "static" / "css").rglob("*.css"))
TARGETS += list((ROOT / "templates").rglob("*.html"))
TARGETS += list((ROOT / "baay" / "templates").rglob("*.html"))

# Un nom de custom property = --[a-z0-9-]+
PROP = re.compile(r"--[a-z0-9]+(?:-[a-z0-9]+)*", re.IGNORECASE)


def remap(token: str) -> str | None:
    """Retourne le nouveau nom, ou None si inchange."""
    if token.startswith("--ab-"):
        return None
    if any(token.startswith(v) for v in VENDOR_PREFIXES):
        return None
    for pfx in LEGACY_PREFIXES:
        if token.startswith(pfx):
            suffix = token[len("--"):]      # "pd-foo" / "space-1"
            return f"--ab-{suffix}"
    return None


def process(text: str) -> tuple[str, int]:
    count = 0

    def _sub(m: "re.Match[str]") -> str:
        nonlocal count
        new = remap(m.group(0))
        if new:
            count += 1
            return new
        return m.group(0)

    return PROP.sub(_sub, text), count


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    total = 0
    touched = 0
    for path in TARGETS:
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        migrated, n = process(original)
        if n:
            total += n
            touched += 1
            label = "WOULD FIX" if args.dry_run else "FIXED"
            print(f"{label} {n:>4}  {path.relative_to(ROOT)}")
            if args.apply:
                path.with_suffix(path.suffix + ".bak").write_text(original, encoding="utf-8")
                path.write_text(migrated, encoding="utf-8")

    print(f"\n{total} remplacements dans {touched} fichiers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
