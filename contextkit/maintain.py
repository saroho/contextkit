"""Maintain operations: archive rotation and task archival."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .files import FILE_TO_ARCHIVE, read_text, write_text


def rotate_file_if_needed(
    ai_dir: Path, file_name: str, line_threshold: int, keep_last: int, now_token: str
) -> tuple[str, str] | None:
    """Archive file content if it exceeds threshold, keep last N lines."""
    file_path = ai_dir / file_name
    if not file_path.exists():
        return None

    lines = read_text(file_path).splitlines()
    if len(lines) <= line_threshold:
        return None

    archive_key = FILE_TO_ARCHIVE[file_name]
    archive_path = ai_dir / "archive" / archive_key / f"{file_path.stem}_{now_token}.md"

    # Archive full content
    write_text(archive_path, "\n".join(lines).strip() + "\n")

    # Keep only last N lines in active file
    kept = lines[-keep_last:] if keep_last > 0 else []
    write_text(file_path, ("\n".join(kept)).strip() + ("\n" if kept else ""))

    return str(archive_path), str(file_path)


def archive_old_completed_tasks(ai_dir: Path, days: int, now_token: str) -> tuple[str, str] | None:
    """Move completed tasks older than N days to archive."""
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


def run_maintain(
    root: Path,
    line_threshold: int = 100,
    keep_last: int = 60,
    task_days: int = 30,
    dry_run: bool = False,
    explain: bool = False,
) -> int:
    """Run maintenance: rotate large files and archive old tasks."""
    from .files import ensure_structure

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


def run_all(
    root: Path,
    force: bool = False,
    line_threshold: int = 100,
    keep_last: int = 60,
    task_days: int = 30,
    dry_run: bool = False,
    explain: bool = False,
) -> int:
    """Run init + maintain."""
    from .commands import run_init

    run_init(root, force=force)
    return run_maintain(
        root,
        line_threshold=line_threshold,
        keep_last=keep_last,
        task_days=task_days,
        dry_run=dry_run,
        explain=explain,
    )
