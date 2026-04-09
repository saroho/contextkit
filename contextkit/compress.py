"""Compress: LLM-driven per-file summarization protocol.

This module orchestrates the end-of-session compression workflow:
1. Displays each accumulating .ai file with targeted compression instructions
2. AI reads the output and writes compressed versions
3. Archives the originals after compression
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .files import (
    COMPRESSIBLE_FILES,
    FILE_TO_ARCHIVE,
    read_text,
    write_text,
    ensure_structure,
)

# Per-file compression strategies
COMPRESSION_STRATEGIES = {
    "DECISIONS.md": {
        "max_lines": 50,
        "keep": "Active/proposed decisions in full, closed decisions as 1-line summaries",
        "drop": "Superseded decisions, stale proposals",
    },
    "DESIGN.md": {
        "max_lines": 60,
        "keep": "Current architecture, active components, live API contracts",
        "drop": "Obsolete sections, placeholder content, deprecated patterns",
    },
    "LESSONS.md": {
        "max_lines": 40,
        "keep": "All lessons (they're short), merge similar ones",
        "drop": "None - lessons are always valuable",
    },
    "PATTERNS.md": {
        "max_lines": 40,
        "keep": "Active conventions, naming rules, structural patterns",
        "drop": "Duplicate patterns, outdated conventions",
    },
    "RELEASE.md": {
        "max_lines": 30,
        "keep": "Last 3 releases with full details",
        "drop": "Old releases (archived)",
    },
    "REQUIREMENTS.md": {
        "max_lines": 40,
        "keep": "Active requirements (Proposed/In Progress), status rollup of completed ones",
        "drop": "Completed requirement details (archived)",
    },
    "TASKS.md": {
        "max_lines": 30,
        "keep": "Active tasks + last 5 completed",
        "drop": "Old completed tasks (archived separately)",
    },
    "TESTING.md": {
        "max_lines": 20,
        "keep": "Current coverage numbers, known gaps, key benchmarks",
        "drop": "Historical coverage data, resolved gaps",
    },
}

SEPARATOR = "═" * 60
DIVIDER = "─" * 60


def _build_compress_prompt(file_name: str, content: str) -> str:
    """Build a targeted compression prompt for a single file."""
    strategy = COMPRESSION_STRATEGIES.get(file_name, {
        "max_lines": 40,
        "keep": "Most important information",
        "drop": "Redundant or obsolete information",
    })

    return f"""{SEPARATOR}
COMPRESS: {file_name}
{SEPARATOR}

Current content ({len(content.splitlines())} lines):

{content}

{DIVIDER}
AI: Compress this file to max {strategy['max_lines']} lines.

KEEP: {strategy['keep']}
DROP: {strategy['drop']}

Write the compressed version below, replacing the file content.
Preserve the markdown header structure (## and ### headers).
{DIVIDER}
"""


def _compress_tasks(ai_dir: Path) -> tuple[int, int]:
    """Special handling for TASKS.md: keep active + recent completed."""
    tasks_path = ai_dir / "TASKS.md"
    if not tasks_path.exists():
        return 0, 0

    text = read_text(tasks_path)
    lines = text.splitlines()

    active_lines = []
    completed_lines = []
    in_active = False
    in_recent = False

    for line in lines:
        if line.startswith("## Active Tasks"):
            in_active = True
            in_recent = False
            active_lines.append(line)
        elif line.startswith("## Recently Completed"):
            in_active = False
            in_recent = True
            completed_lines.append(line)
        elif in_active and line.strip():
            active_lines.append(line)
        elif in_recent and line.strip():
            completed_lines.append(line)

    # Keep all active lines, last 5 completed
    recent_completed = completed_lines[:1] + completed_lines[-5:] if len(completed_lines) > 6 else completed_lines
    new_lines = active_lines + [""] + recent_completed if recent_completed else active_lines

    old_count = len(lines)
    new_content = "\n".join(new_lines).rstrip() + "\n"
    write_text(tasks_path, new_content)

    return old_count, len(new_lines)


def _compress_releases(ai_dir: Path) -> tuple[int, int]:
    """Keep only last 3 releases."""
    release_path = ai_dir / "RELEASE.md"
    if not release_path.exists():
        return 0, 0

    text = read_text(release_path)
    lines = text.splitlines()

    # Find all ### [version] sections
    release_starts = []
    for i, line in enumerate(lines):
        if re.match(r"### \[v", line):
            release_starts.append(i)

    # Find the ## Release History header
    header_end = 0
    for i, line in enumerate(lines):
        if line.startswith("## "):
            header_end = i + 1
            break

    if len(release_starts) <= 3:
        return len(lines), len(lines)

    # Keep header + last 3 releases
    keep_indices = set(range(header_end))
    for start in release_starts[-3:]:
        # Find end of this release section
        end = start + 1
        while end < len(lines) and not lines[end].startswith("### ["):
            end += 1
        keep_indices.update(range(start, end))

    new_lines = [lines[i] for i in range(len(lines)) if i in keep_indices]
    old_count = len(lines)
    new_content = "\n".join(new_lines).rstrip() + "\n"
    write_text(release_path, new_content)

    return old_count, len(new_lines)


def run_compress(ai_dir: Path, auto_archive: bool = True) -> int:
    """Display compression prompts for all accumulating files.

    This command is designed to be read by the AI agent, which then
    writes compressed versions of each file. After compression, the
    originals are automatically archived.
    """
    ai_dir = ensure_structure(ai_dir.parent if ai_dir.name == ".ai" else ai_dir)

    # Ensure all files exist
    for file_name in COMPRESSIBLE_FILES:
        path = ai_dir / file_name
        if not path.exists():
            write_text(path, "")

    print(f"\n{SEPARATOR}")
    print(f"CONTEXTKIT COMPRESS — End-of-Session Compression")
    print(f"{SEPARATOR}")
    print(f"\nAI: Read each file below and write a compressed version.")
    print(f"Then run 'contextkit compress --write <FILE>' with your summary.")
    print(f"\n{SEPARATOR}\n")

    total_lines = 0
    for file_name in COMPRESSIBLE_FILES:
        path = ai_dir / file_name
        content = read_text(path)
        if not content.strip():
            print(f"[skip] {file_name}: empty")
            continue

        total_lines += len(content.splitlines())
        print(_build_compress_prompt(file_name, content))

    print(f"\n{SEPARATOR}")
    print(f"TOTAL: {len(COMPRESSIBLE_FILES)} files, {total_lines} lines to review")
    print(f"{SEPARATOR}")
    print(f"""
AI INSTRUCTIONS:
1. Read each COMPRESS block above
2. For each file, run:
   contextkit compress --write {file_name} "compressed content"
   OR edit the file directly with the compressed version
3. After all files are compressed, originals are auto-archived

Alternatively, edit the files directly in your editor.
{SEPARATOR}
""")

    return 0


def run_compress_write(ai_dir: Path, file_name: str, content: str, archive_original: bool = True) -> int:
    """Write compressed content for a single file.

    Called by the AI after it has produced a compressed version.
    """
    target_path = ai_dir / file_name

    if not target_path.exists():
        print(f"ERROR: {file_name} not found. Run 'contextkit init' first.")
        return 1

    if archive_original:
        now_token = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_key = FILE_TO_ARCHIVE.get(file_name)
        if archive_key:
            archive_path = ai_dir / "archive" / archive_key / f"{target_path.stem}_pre_compress_{now_token}.md"
            original = read_text(target_path)
            write_text(archive_path, original.strip() + "\n")
            print(f"[archive] {file_name} -> {archive_path.name}")

    write_text(target_path, content.strip() + "\n")
    new_lines = len(content.splitlines())
    print(f"[+] {file_name} compressed to {new_lines} lines")
    return 0
