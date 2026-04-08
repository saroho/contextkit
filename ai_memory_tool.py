#!/usr/bin/env python3
"""Single-file tool to bootstrap and maintain the .ai memory system."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import sys

CORE_FILES = [
    "README.md",
    "CONTEXT.md",
    "DECISIONS.md",
    "PATTERNS.md",
    "LESSONS.md",
    "TASKS.md",
]

ARCHIVE_DIRS = ["context", "decisions", "patterns", "lessons", "tasks"]

FILE_TO_ARCHIVE = {
    "CONTEXT.md": "context",
    "DECISIONS.md": "decisions",
    "PATTERNS.md": "patterns",
    "LESSONS.md": "lessons",
    "TASKS.md": "tasks",
}

DEFAULT_TEMPLATES = {
    "README.md": """# AI Memory System

## Goal
Keep persistent project context across AI sessions.

## Core Files
- CONTEXT.md
- DECISIONS.md
- PATTERNS.md
- LESSONS.md
- TASKS.md
""",
    "CONTEXT.md": """## Current Session
<!-- Updated: -->

### Active Task

### Context

### Recent Changes

### Blockers

### Next Steps
""",
    "DECISIONS.md": """## Architecture Decisions

### [001] Title
- **Status**: Proposed
- **Context**:
- **Decision**:
- **Consequences**:
- **Date**:
""",
    "PATTERNS.md": """## Code Patterns

### Structure

### Naming

### Patterns

### Anti-patterns
""",
    "LESSONS.md": """## Lessons Learned

### [DATE] Title
- **Symptom**:
- **Root Cause**:
- **Fix**:
- **Prevention**:
""",
    "TASKS.md": """## Active Tasks

## Recently Completed (Last 30 Days)
""",
}


@dataclass
class Summary:
    created: list[str]
    skipped: list[str]
    archived: list[str]
    updated: list[str]

    def __init__(self) -> None:
        self.created = []
        self.skipped = []
        self.archived = []
        self.updated = []


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ensure_structure(root: Path, summary: Summary) -> Path:
    ai_dir = root / ".ai"
    archive_dir = ai_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for name in ARCHIVE_DIRS:
        p = archive_dir / name
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            summary.created.append(str(p))
    return ai_dir


def template_content(root: Path, file_name: str) -> str:
    template_path = root / "templates" / file_name
    if template_path.exists():
        return read_text(template_path)
    return DEFAULT_TEMPLATES[file_name]


def init_files(root: Path, force: bool, summary: Summary) -> None:
    ai_dir = ensure_structure(root, summary)
    for file_name in CORE_FILES:
        target = ai_dir / file_name
        if target.exists() and not force:
            summary.skipped.append(str(target))
            continue
        write_text(target, template_content(root, file_name))
        if target.exists():
            summary.created.append(str(target))


def rotate_large_files(
    root: Path,
    line_threshold: int,
    keep_last: int,
    summary: Summary,
) -> None:
    ai_dir = ensure_structure(root, summary)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    for file_name, archive_key in FILE_TO_ARCHIVE.items():
        file_path = ai_dir / file_name
        if not file_path.exists():
            continue
        lines = read_text(file_path).splitlines()
        if len(lines) <= line_threshold:
            continue
        archive_path = ai_dir / "archive" / archive_key / f"{file_path.stem}_{now}.md"
        write_text(archive_path, "\n".join(lines).strip() + "\n")
        kept = lines[-keep_last:] if keep_last > 0 else []
        write_text(file_path, ("\n".join(kept)).strip() + ("\n" if kept else ""))
        summary.archived.append(str(archive_path))
        summary.updated.append(str(file_path))


def archive_old_completed_tasks(root: Path, days: int, summary: Summary) -> None:
    ai_dir = ensure_structure(root, summary)
    tasks_path = ai_dir / "TASKS.md"
    if not tasks_path.exists():
        return

    text = read_text(tasks_path)
    lines = text.splitlines()
    today = datetime.now().date()
    completed_line = re.compile(r"^- \[x\].*?(\d{4}-\d{2}-\d{2})")

    keep: list[str] = []
    to_archive: list[str] = []

    for line in lines:
        match = completed_line.search(line)
        if not match:
            keep.append(line)
            continue
        try:
            done_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except ValueError:
            keep.append(line)
            continue
        age = (today - done_date).days
        if age > days:
            to_archive.append(line)
        else:
            keep.append(line)

    if not to_archive:
        return

    archive_name = datetime.now().strftime("TASKS_completed_%Y%m%d.md")
    archive_path = ai_dir / "archive" / "tasks" / archive_name
    previous = read_text(archive_path)
    combined = (previous.strip() + "\n" if previous.strip() else "") + "\n".join(to_archive) + "\n"
    write_text(archive_path, combined)
    write_text(tasks_path, "\n".join(keep).rstrip() + "\n")
    summary.archived.append(str(archive_path))
    summary.updated.append(str(tasks_path))


def print_summary(summary: Summary) -> None:
    if summary.created:
        print("Created:")
        for item in summary.created:
            print(f"  - {item}")
    if summary.archived:
        print("Archived:")
        for item in summary.archived:
            print(f"  - {item}")
    if summary.updated:
        print("Updated:")
        for item in summary.updated:
            print(f"  - {item}")
    if summary.skipped:
        print("Skipped (already exists):")
        for item in summary.skipped:
            print(f"  - {item}")
    if not any([summary.created, summary.archived, summary.updated, summary.skipped]):
        print("No changes.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage .ai memory files without platform-specific skills.")
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create missing .ai files and archive structure.")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing core files.")

    p_maintain = sub.add_parser("maintain", help="Rotate large files and archive old completed tasks.")
    p_maintain.add_argument("--line-threshold", type=int, default=100, help="Rotate file if line count exceeds this.")
    p_maintain.add_argument("--keep-last", type=int, default=60, help="After rotation, keep this many lines.")
    p_maintain.add_argument("--task-days", type=int, default=30, help="Archive completed tasks older than this.")

    p_all = sub.add_parser("all", help="Run init and maintain in one command.")
    p_all.add_argument("--force", action="store_true", help="Overwrite existing core files in init step.")
    p_all.add_argument("--line-threshold", type=int, default=100, help="Rotate file if line count exceeds this.")
    p_all.add_argument("--keep-last", type=int, default=60, help="After rotation, keep this many lines.")
    p_all.add_argument("--task-days", type=int, default=30, help="Archive completed tasks older than this.")

    sub.add_parser("status", help="Show missing core files and simple line counts.")
    return parser


def status(root: Path) -> int:
    ai_dir = root / ".ai"
    print(f"Project root: {root.resolve()}")
    print(f".ai exists: {ai_dir.exists()}")
    missing = []
    for name in CORE_FILES:
        p = ai_dir / name
        if not p.exists():
            missing.append(name)
            continue
        line_count = len(read_text(p).splitlines())
        print(f"  - {name}: {line_count} lines")
    if missing:
        print("Missing:")
        for name in missing:
            print(f"  - {name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    summary = Summary()

    if args.command == "init":
        init_files(root, force=args.force, summary=summary)
        print_summary(summary)
        return 0
    if args.command == "maintain":
        rotate_large_files(root, args.line_threshold, args.keep_last, summary)
        archive_old_completed_tasks(root, args.task_days, summary)
        print_summary(summary)
        return 0
    if args.command == "all":
        init_files(root, force=args.force, summary=summary)
        rotate_large_files(root, args.line_threshold, args.keep_last, summary)
        archive_old_completed_tasks(root, args.task_days, summary)
        print_summary(summary)
        return 0
    if args.command == "status":
        return status(root)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
