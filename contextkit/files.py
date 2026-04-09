"""File I/O, templates, and markdown helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

CORE_FILES = [
    "README.md",
    "CONTEXT.md",
    "REQUIREMENTS.md",
    "DESIGN.md",
    "DECISIONS.md",
    "PATTERNS.md",
    "LESSONS.md",
    "TESTING.md",
    "TASKS.md",
    "RELEASE.md",
]

ARCHIVE_DIRS = ["context", "requirements", "design", "decisions", "patterns", "lessons", "testing", "tasks", "releases"]

FILE_TO_ARCHIVE = {
    "CONTEXT.md": "context",
    "REQUIREMENTS.md": "requirements",
    "DESIGN.md": "design",
    "DECISIONS.md": "decisions",
    "PATTERNS.md": "patterns",
    "LESSONS.md": "lessons",
    "TESTING.md": "testing",
    "TASKS.md": "tasks",
    "RELEASE.md": "releases",
}

# Files that benefit from AI compression (excluding README, CONTEXT, and system files)
COMPRESSIBLE_FILES = [
    "DECISIONS.md",
    "DESIGN.md",
    "LESSONS.md",
    "PATTERNS.md",
    "RELEASE.md",
    "REQUIREMENTS.md",
    "TASKS.md",
    "TESTING.md",
]

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
""",
    "PATTERNS.md": """## Code Patterns
""",
    "LESSONS.md": """## Lessons Learned
""",
    "TASKS.md": """## Active Tasks

## Recently Completed (Last 30 Days)
""",
    "REQUIREMENTS.md": """## Features & Requirements
""",
    "DESIGN.md": """## System Design

### Architecture Overview

### Backend Components

### Frontend / UI Components

### UI/UX Patterns

### Data Models

### API Contracts

### State Management

### External Dependencies
""",
    "TESTING.md": """## Testing Strategy

### Test Coverage
- Unit Tests: [0]%
- Integration Tests: [0]%
- E2E Tests: [0]%

### Known Test Gaps

### Performance Benchmarks
""",
    "RELEASE.md": """## Release History
""",
}


def read_text(path: Path) -> str:
    """Read text file with encoding fallbacks."""
    if not path.exists():
        return ""
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    """Write text file, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ensure_structure(root: Path) -> Path:
    """Create .ai/ directory and archive subdirectories."""
    ai_dir = root / ".ai"
    archive_dir = ai_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for name in ARCHIVE_DIRS:
        p = archive_dir / name
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
    return ai_dir


# --- Markdown compacting ---

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
    """Remove ### sections that have no body content."""
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
    """Compact markdown text: collapse blanks, prune empty sections."""
    raw_lines = [ln.rstrip() for ln in text.splitlines()]
    raw_lines = _collapse_blank_lines(raw_lines, max_run=1)
    compacted = "\n".join(raw_lines).strip()
    if file_name in {"CONTEXT.md", "PATTERNS.md", "LESSONS.md"}:
        compacted = _prune_empty_h3_sections(compacted).strip()
        compacted = "\n".join(_collapse_blank_lines(compacted.splitlines(), max_run=1)).strip()
    return compacted + ("\n" if compacted else "")
