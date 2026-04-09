"""Minimal CLI: init, status, archive."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .files import (
    CORE_FILES,
    MEMORY_TEMPLATE,
    DESIGN_TEMPLATE,
    read_text,
    write_text,
    ensure_structure,
    compact,
)


def run_init(root: Path, force: bool) -> int:
    ai_dir = ensure_structure(root)
    created = []
    skipped = []
    for name, template in [("MEMORY.md", MEMORY_TEMPLATE), ("DESIGN.md", DESIGN_TEMPLATE)]:
        target = ai_dir / name
        if target.exists() and not force:
            skipped.append(name)
            continue
        write_text(target, template)
        created.append(name)
    if created:
        print("Created: " + ", ".join(created))
    if skipped:
        print("Skipped (exists): " + ", ".join(skipped))
    return 0


def run_status(root: Path) -> int:
    ai_dir = root / ".ai"
    print(f"Project: {root.resolve()}")
    print(f".ai: {ai_dir.exists()}")
    for name in CORE_FILES:
        p = ai_dir / name
        if p.exists():
            text = read_text(p)
            print(f"  {name}: {len(text.splitlines())} lines, {len(text)} chars")
        else:
            print(f"  {name}: MISSING")
    return 0


def run_archive(root: Path, line_threshold: int = 150, dry_run: bool = False) -> int:
    """Archive files exceeding line threshold, keep file clean."""
    ai_dir = ensure_structure(root)
    archived = []
    updated = []

    for name in CORE_FILES:
        path = ai_dir / name
        if not path.exists():
            continue
        text = read_text(path)
        lines = text.splitlines()
        if len(lines) <= line_threshold:
            continue
        if dry_run:
            print(f"Would archive {name} ({len(lines)} lines)")
            continue
        # Save full version to archive
        token = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = ai_dir / "archive" / f"{name.rstrip('.md')}_{token}.md"
        write_text(archive_path, compact(text))
        archived.append(f"{name} -> {archive_path.name}")
        # Keep file as-is (AI is responsible for keeping it compressed)
        # We just archive a copy for safety, don't truncate
        updated.append(name)

    if dry_run:
        return 0
    if archived:
        print("Archived:")
        for item in archived:
            print(f"  {item}")
    else:
        print("Nothing to archive.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextkit",
        description="Minimal project memory for AI coding agents.",
    )
    parser.add_argument("--root", default=".", help="Project root.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create .ai/ memory files.").add_argument(
        "--force", action="store_true", help="Overwrite existing."
    )
    sub.add_parser("status", help="Show memory file sizes.")

    p_arch = sub.add_parser("archive", help="Archive files exceeding threshold.")
    p_arch.add_argument("--line-threshold", type=int, default=150)
    p_arch.add_argument("--dry-run", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.command == "init":
        return run_init(root, force=getattr(args, "force", False))
    if args.command == "status":
        return run_status(root)
    if args.command == "archive":
        return run_archive(root, line_threshold=args.line_threshold, dry_run=args.dry_run)

    parser.print_help()
    return 1


def cli() -> None:
    raise SystemExit(main())
