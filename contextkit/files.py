"""File I/O and templates for ContextKit v0.5.0 — simplified memory system."""

from __future__ import annotations

from pathlib import Path


CORE_FILES = ["MEMORY.md", "DESIGN.md"]

MEMORY_TEMPLATE = """\
## Active Task

## Current Context

## Key Decisions

## Code Patterns

## Gotchas & Lessons

## Next Steps
"""

DESIGN_TEMPLATE = """\
## Architecture
"""


def read_text(path: Path) -> str:
    """Read text with encoding fallback."""
    if not path.exists():
        return ""
    for enc in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    """Write text, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ensure_structure(root: Path) -> Path:
    """Create .ai/ and archive/ directories."""
    ai_dir = root / ".ai"
    (ai_dir / "archive").mkdir(parents=True, exist_ok=True)
    return ai_dir


def compact(text: str) -> str:
    """Remove excessive blank lines, strip trailing whitespace."""
    lines = text.splitlines()
    out: list[str] = []
    blanks = 0
    for line in lines:
        stripped = line.rstrip()
        if stripped == "":
            blanks += 1
            if blanks <= 1:
                out.append("")
        else:
            blanks = 0
            out.append(stripped)
    result = "\n".join(out).strip()
    return result + "\n" if result else ""
