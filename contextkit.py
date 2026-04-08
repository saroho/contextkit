#!/usr/bin/env python3
"""Single-file tool to bootstrap and maintain the .ai memory system."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

CORE_FILES = [
    "README.md",
    "CONTEXT.md",
    "DECISIONS.md",
    "PATTERNS.md",
    "LESSONS.md",
    "TASKS.md",
]

ARCHIVE_DIRS = ["context", "decisions", "patterns", "lessons", "tasks", "plans"]

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


# --- Utilities ---

def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _collapse_blank_lines(lines: list[str], max_run: int = 1) -> list[str]:
    out: list[str] = []
    run = 0
    for line in lines:
        if line.strip() == "":
            run += 1
            if run > max_run:
                continue
            out.append("")
        else:
            run = 0
            out.append(line.rstrip())
    return out


def _prune_empty_h3_sections(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("### "):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("### "):
                if lines[j].startswith("## "):
                    break
                j += 1
            block = lines[i:j]
            body = [x for x in block[1:] if x.strip() and not x.strip().startswith("<!--")]
            if not body:
                i = j
                continue
            out.extend(block)
            i = j
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def compact_markdown(text: str, file_name: str) -> str:
    raw_lines = [ln.rstrip() for ln in text.splitlines()]
    raw_lines = _collapse_blank_lines(raw_lines, max_run=1)
    compacted = "\n".join(raw_lines).strip()
    if file_name in {"CONTEXT.md", "PATTERNS.md", "LESSONS.md"}:
        compacted = _prune_empty_h3_sections(compacted).strip()
        compacted = "\n".join(_collapse_blank_lines(compacted.splitlines(), max_run=1)).strip()
    return compacted + ("\n" if compacted else "")


# --- Init ---

def ensure_structure(root: Path) -> Path:
    ai_dir = root / ".ai"
    archive_dir = ai_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for name in ARCHIVE_DIRS:
        p = archive_dir / name
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
    return ai_dir


def run_init(root: Path, force: bool) -> int:
    ai_dir = ensure_structure(root)
    created = []
    skipped = []
    for file_name in CORE_FILES:
        target = ai_dir / file_name
        if target.exists() and not force:
            skipped.append(str(target))
            continue
        write_text(target, DEFAULT_TEMPLATES[file_name])
        if target.exists():
            created.append(str(target))
    if created:
        print("Created:")
        for item in created:
            print(f"  - {item}")
    if skipped:
        print("Skipped (already exists):")
        for item in skipped:
            print(f"  - {item}")
    if not created and not skipped:
        print("No changes.")
    return 0


# --- Maintain: file rotation ---

def rotate_file_if_needed(ai_dir: Path, file_name: str, line_threshold: int, keep_last: int, now_token: str) -> tuple[str, str] | None:
    file_path = ai_dir / file_name
    if not file_path.exists():
        return None
    lines = read_text(file_path).splitlines()
    if len(lines) <= line_threshold:
        return None
    archive_key = FILE_TO_ARCHIVE[file_name]
    archive_path = ai_dir / "archive" / archive_key / f"{file_path.stem}_{now_token}.md"
    write_text(archive_path, "\n".join(lines).strip() + "\n")
    kept = lines[-keep_last:] if keep_last > 0 else []
    write_text(file_path, ("\n".join(kept)).strip() + ("\n" if kept else ""))
    return str(archive_path), str(file_path)


# --- Maintain: task archival ---

def archive_old_completed_tasks(ai_dir: Path, days: int, now_token: str) -> tuple[str, str] | None:
    tasks_path = ai_dir / "TASKS.md"
    if not tasks_path.exists():
        return None
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
        if (today - done_date).days > days:
            to_archive.append(line)
        else:
            keep.append(line)

    if not to_archive:
        return None

    archive_path = ai_dir / "archive" / "tasks" / f"TASKS_completed_{now_token[:8]}.md"
    previous = read_text(archive_path)
    combined = (previous.strip() + "\n" if previous.strip() else "") + "\n".join(to_archive) + "\n"
    write_text(archive_path, combined)
    updated = "\n".join(keep).rstrip() + "\n"
    write_text(tasks_path, updated)
    return str(archive_path), str(tasks_path)


# --- Maintain command ---

def run_maintain(root: Path, line_threshold: int, keep_last: int, task_days: int, dry_run: bool, explain: bool) -> int:
    ai_dir = ensure_structure(root)
    now_token = datetime.now().strftime("%Y%m%d_%H%M%S")

    archived = []
    updated = []

    # Rotate large files
    for file_name in FILE_TO_ARCHIVE:
        file_path = ai_dir / file_name
        if not file_path.exists():
            continue
        line_count = len(read_text(file_path).splitlines())
        if line_count <= line_threshold:
            continue
        if explain:
            print(f"Rotate {file_name} lines={line_count} threshold={line_threshold} keep_last={keep_last}")
        if not dry_run:
            result = rotate_file_if_needed(ai_dir, file_name, line_threshold, keep_last, now_token)
            if result:
                arch_path, upd_path = result
                archived.append(arch_path)
                updated.append(upd_path)

    # Archive old completed tasks
    tasks_path = ai_dir / "TASKS.md"
    if tasks_path.exists():
        to_archive_count = 0
        text = read_text(tasks_path)
        today = datetime.now().date()
        completed_line = re.compile(r"^- \[x\].*?(\d{4}-\d{2}-\d{2})")
        for line in text.splitlines():
            match = completed_line.search(line)
            if match:
                try:
                    done_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
                    if (today - done_date).days > task_days:
                        to_archive_count += 1
                except ValueError:
                    pass
        if to_archive_count > 0 and explain:
            print(f"Archive tasks count={to_archive_count} days={task_days}")
        if not dry_run:
            result = archive_old_completed_tasks(ai_dir, task_days, now_token)
            if result:
                arch_path, upd_path = result
                archived.append(arch_path)
                updated.append(upd_path)

    if archived:
        print("Archived:")
        for item in archived:
            print(f"  - {item}")
    if updated:
        print("Updated:")
        for item in updated:
            print(f"  - {item}")
    if not archived and not updated:
        print("Nothing to do.")
    return 0


# --- All command ---

def run_all(root: Path, force: bool, line_threshold: int, keep_last: int, task_days: int, dry_run: bool, explain: bool) -> int:
    run_init(root, force=force)
    return run_maintain(root, line_threshold=line_threshold, keep_last=keep_last, task_days=task_days, dry_run=dry_run, explain=explain)


# --- Status command ---

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


# --- Parser ---

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage .ai memory files.")
    parser.add_argument("--root", default=".", help="Project root (default: current directory).")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create missing .ai files and archive structure.")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing core files.")

    p_maintain = sub.add_parser("maintain", help="Rotate large files and archive old tasks.")
    p_maintain.add_argument("--line-threshold", type=int, default=100)
    p_maintain.add_argument("--keep-last", type=int, default=60)
    p_maintain.add_argument("--task-days", type=int, default=30)
    p_maintain.add_argument("--dry-run", action="store_true")
    p_maintain.add_argument("--explain", action="store_true")

    p_all = sub.add_parser("all", help="Run init + maintain.")
    p_all.add_argument("--force", action="store_true")
    p_all.add_argument("--line-threshold", type=int, default=100)
    p_all.add_argument("--keep-last", type=int, default=60)
    p_all.add_argument("--task-days", type=int, default=30)
    p_all.add_argument("--dry-run", action="store_true")
    p_all.add_argument("--explain", action="store_true")

    sub.add_parser("status", help="Show missing core files and line counts.")

    return parser


# --- Main ---

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.command == "init":
        return run_init(root, force=getattr(args, "force", False))
    if args.command == "maintain":
        return run_maintain(
            root,
            line_threshold=args.line_threshold,
            keep_last=args.keep_last,
            task_days=args.task_days,
            dry_run=args.dry_run,
            explain=args.explain,
        )
    if args.command == "all":
        return run_all(
            root,
            force=args.force,
            line_threshold=args.line_threshold,
            keep_last=args.keep_last,
            task_days=args.task_days,
            dry_run=args.dry_run,
            explain=args.explain,
        )
    if args.command == "status":
        return status(root)

    parser.print_help()
    return 1


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    sys.exit(main())
