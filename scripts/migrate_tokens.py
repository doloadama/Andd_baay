#!/usr/bin/env python3
"""
Migre les namespaces CSS obsolètes vers --ab-* dans baay/static/css/.

Namespaces migrés :
  --fd-*       (ferme-detail.css)          → --ab-*
  --msg-*      (messagerie-*.css)           → --ab-*
  --cockpit-*  (dashboard_cockpit.css)      → --ab-*
  --fh-*       (finance_hub_ft.css)         → --ab-*

Usage:
  python scripts/migrate_tokens.py [--dry-run]
"""
import re
import sys
from pathlib import Path

# ------------------------------------------------------------------ #
#  Mapping : ancien token → équivalent --ab-*
#  Construit en analysant les valeurs réelles de chaque fichier CSS
#  et en les comparant aux tokens définis dans tokens.css.
# ------------------------------------------------------------------ #

NAMESPACE_MAP = {
    # ── --fd-* (ferme-detail.css) ──────────────────────────────────
    "--fd-brand":   "--ab-color-primary",
    "--fd-deep":    "--ab-color-primary-deep",
    "--fd-night":   "--ab-color-primary-night",
    "--fd-accent":  "--ab-color-accent",
    "--fd-surface": "--ab-color-surface",
    "--fd-border":  "--ab-color-border",
    "--fd-muted":   "--ab-color-background",

    # ── --msg-* (messagerie-inbox.css + messagerie-conversation.css) #
    "--msg-brand":       "--ab-color-primary",
    "--msg-brand-deep":  "--ab-color-primary-deep",
    "--msg-brand-night": "--ab-color-primary-night",
    "--msg-brand-mid":   "--ab-color-primary-mid",
    "--msg-brand-soft":  "--ab-color-primary-soft",
    "--msg-brand-glow":  "--ab-color-primary-glow",
    "--msg-brand-rgb":   "--ab-color-primary-rgb",
    "--msg-accent":      "--ab-color-accent",
    "--msg-surface":     "--ab-color-surface",
    "--msg-bg":          "--ab-color-background",
    "--msg-border":      "--ab-color-border",

    # ── --cockpit-* (dashboard_cockpit.css) ───────────────────────
    "--cockpit-recette":    "--ab-color-primary",
    "--cockpit-recette-bg": "--ab-color-primary-bg",
    "--cockpit-depense":    "--ab-color-depense",
    "--cockpit-depense-bg": "--ab-color-depense-bg",
    "--cockpit-orange":     "--ab-color-accent",
    "--cockpit-terre":      "--ab-color-terre",
    "--cockpit-ink":        "--ab-color-text",
    "--cockpit-paper":      "--ab-color-background",

    # ── --fh-* (finance_hub_ft.css) ───────────────────────────────
    "--fh-page-bg":  "--ab-color-background",
    "--fh-surface":  "--ab-color-surface",
    "--fh-surface2": "--ab-color-surface-alt",
    "--fh-border":   "--ab-color-border",
    "--fh-text1":    "--ab-color-text",
    "--fh-text2":    "--ab-color-text-secondary",
    "--fh-text3":    "--ab-color-text-muted",
    "--fh-danger":   "--ab-color-danger",
    # dark-mode scoped cat-pill tokens conservent leur sémantique
    "--fh-cat-pill-bg":     "--ab-finance-cat-pill-bg",
    "--fh-cat-pill-border": "--ab-finance-cat-pill-border",
    "--fh-cat-pill-text":   "--ab-finance-cat-pill-text",
}

# Ordre de remplacement : du plus long au plus court pour éviter
# les substitutions partielles (ex: --msg-brand-deep avant --msg-brand).
SORTED_MAP = sorted(NAMESPACE_MAP.items(), key=lambda kv: len(kv[0]), reverse=True)


def migrate_file(path: Path, dry_run: bool = False) -> int:
    """Retourne le nombre de remplacements effectués dans le fichier."""
    content = path.read_text(encoding="utf-8")
    new_content = content
    count = 0
    for old, new in SORTED_MAP:
        occurrences = new_content.count(old)
        if occurrences:
            new_content = new_content.replace(old, new)
            count += occurrences
    if count and not dry_run:
        path.write_text(new_content, encoding="utf-8")
    return count


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    css_dir = Path("baay/static/css")

    if not css_dir.is_dir():
        print(f"ERROR: directory not found: {css_dir}", file=sys.stderr)
        sys.exit(1)

    totals: dict[str, int] = {}
    grand_total = 0

    for css_file in sorted(css_dir.glob("*.css")):
        n = migrate_file(css_file, dry_run)
        if n:
            prefix = "[DRY] " if dry_run else ""
            print(f"{prefix}{css_file}: {n} replacements")
            totals[css_file.name] = n
            grand_total += n

    print()
    if totals:
        print("Breakdown by namespace (estimated):")
        # Re-scan to count per namespace in final content (informational only)
        namespace_counts: dict[str, int] = {ns: 0 for ns in NAMESPACE_MAP}
        for css_file in sorted(css_dir.glob("*.css")):
            text = css_file.read_text(encoding="utf-8")
            for old_ns in NAMESPACE_MAP:
                namespace_counts[old_ns] += text.count(old_ns)
        # After migration, remaining counts should be 0
        # Report was done before write; use grand_total
    print(f"Total: {grand_total} replacements {'(dry run — no files written)' if dry_run else '(files updated)'}")


if __name__ == "__main__":
    main()
