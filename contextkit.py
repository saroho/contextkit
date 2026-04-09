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
    "REQUIREMENTS.md": """## Features & Requirements

### [REQ-001] Feature Name
- **Priority**: High / Medium / Low
- **Status**: Proposed / In Progress / Done
- **User Story**: As a [user], I want [goal] so that [benefit]
- **Acceptance Criteria**:
  - [ ] [Criterion 1]
  - [ ] [Criterion 2]
- **Date**: 2026-04-09
""",
    "DESIGN.md": """## System Design

### Architecture Overview
[High-level description, component diagram]

### Backend Components
#### [Component Name]
- **Purpose**: [What it does]
- **Interfaces**: [APIs, events]
- **Dependencies**: [What it relies on]

### Frontend / UI Components
#### [Component Name]
- **Purpose**: [UI purpose, user interaction]
- **State**: [Local state, global state]
- **Props/Inputs**: [Data flow]
- **Events/Outputs**: [User actions emitted]

### UI/UX Patterns
#### [Pattern Name]
- **When**: [Where to use]
- **Layout**: [Grid, flex, positioning]
- **Accessibility**: [ARIA, keyboard nav, screen reader]
- **Responsive**: [Breakpoints, mobile considerations]

### Data Models
#### [Model Name]
[Fields, relationships]

### API Contracts
#### [Endpoint Name]
- **Method**: GET/POST/PUT/DELETE
- **Path**: `/api/...`
- **Request**: [Body, params]
- **Response**: [Status codes, schema]

### State Management
- **Global State**: [Redux/Context/etc, what's stored]
- **Local State**: [Component-level patterns]
- **Server State**: [Caching, invalidation strategy]

### External Dependencies
- [Service/Library]: [Why, version, alternatives considered]
""",
    "TESTING.md": """## Testing Strategy

### Test Coverage
- Unit Tests: [X]%
- Integration Tests: [X]%
- E2E Tests: [X]%

### Test Commands
```bash
# Run all tests
[command]

# Run with coverage
[command]
```

### Known Test Gaps
- [Area not covered, why]
- [Flaky tests, known issues]

### Performance Benchmarks
- [Metric]: [Value] ([threshold])
""",
    "RELEASE.md": """## Release History

### [v0.1.0] - 2026-04-09
#### Added
- [New feature/capability]
#### Changed
- [Modified behavior]
#### Fixed
- [Bug fix]
#### Deployment
- [Environment]: [Status, notes]
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


# --- Update commands ---

def get_next_decision_number(ai_dir: Path) -> str:
    """Auto-increment decision number based on year."""
    decisions_path = ai_dir / "DECISIONS.md"
    text = read_text(decisions_path)
    # Find all existing decision numbers like [2026-001] or [001]
    pattern = r"\[(\d{4}-)?(\d+)\]"
    matches = re.findall(pattern, text)
    current_year = datetime.now().year
    
    if not matches:
        return f"{current_year}-001"
    
    # Get the highest number for current year
    year_numbers = []
    for year_prefix, num in matches:
        year = int(year_prefix.split("-")[0]) if year_prefix else current_year
        if year == current_year:
            year_numbers.append(int(num))
    
    next_num = max(year_numbers) + 1 if year_numbers else 1
    return f"{current_year}-{next_num:03d}"


def run_add_decision(ai_dir: Path, title: str, context: str, decision: str, consequences: str, status: str = "Proposed") -> int:
    """Add a new decision to DECISIONS.md."""
    decisions_path = ai_dir / "DECISIONS.md"
    if not decisions_path.exists():
        write_text(decisions_path, DEFAULT_TEMPLATES["DECISIONS.md"])

    num = get_next_decision_number(ai_dir)
    date = datetime.now().strftime("%Y-%m-%d")

    entry = f"""### [{num}] {title}
- **Status**: {status}
- **Context**: {context}
- **Decision**: {decision}
- **Consequences**: {consequences}
- **Date**: {date}
"""

    text = read_text(decisions_path)
    # Insert after the header line
    lines = text.splitlines()
    insert_idx = 1
    for i, line in enumerate(lines):
        if line.startswith("## ") or line.startswith("<!--"):
            insert_idx = i + 1
        elif line.strip() and not line.startswith("##") and not line.startswith("<!--"):
            break

    lines.insert(insert_idx, entry)
    write_text(decisions_path, "\n".join(lines).rstrip() + "\n")
    print(f"✅ Decision [{num}] added: {title}")
    return 0


def run_add_lesson(ai_dir: Path, title: str, symptom: str, root_cause: str, fix: str, prevention: str) -> int:
    """Add a new lesson to LESSONS.md."""
    lessons_path = ai_dir / "LESSONS.md"
    if not lessons_path.exists():
        write_text(lessons_path, DEFAULT_TEMPLATES["LESSONS.md"])

    date = datetime.now().strftime("%Y-%m-%d")

    entry = f"""### [{date}] {title}
- **Symptom**: {symptom}
- **Root Cause**: {root_cause}
- **Fix**: {fix}
- **Prevention**: {prevention}
"""

    text = read_text(lessons_path)
    lines = text.splitlines()
    insert_idx = 1
    for i, line in enumerate(lines):
        if line.startswith("## ") or line.startswith("<!--"):
            insert_idx = i + 1
        elif line.strip() and not line.startswith("##") and not line.startswith("<!--"):
            break

    lines.insert(insert_idx, entry)
    write_text(lessons_path, "\n".join(lines).rstrip() + "\n")
    print(f"✅ Lesson added: {title}")
    return 0


def run_update_context(ai_dir: Path, change: str, context: str = "", blocker: str = "", next_steps: str = "") -> int:
    """Update CONTEXT.md with recent changes."""
    context_path = ai_dir / "CONTEXT.md"
    if not context_path.exists():
        write_text(context_path, DEFAULT_TEMPLATES["CONTEXT.md"])

    text = read_text(context_path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Update timestamp
    text = re.sub(r"<!-- Updated: .*? -->", f"<!-- Updated: {timestamp} -->", text)

    # Add to Recent Changes
    if change:
        text = re.sub(
            r"(### Recent Changes\n)",
            rf"\1- {change}\n",
            text,
            count=1
        )

    # Update Context section if provided
    if context:
        text = re.sub(
            r"(### Context\n)\[.*?\]",
            rf"\1{context}",
            text,
            count=1
        )

    # Update Blockers if provided
    if blocker:
        text = re.sub(
            r"(### Blockers\n)- \[None /.*?\]",
            rf"\1- {blocker}",
            text,
            count=1
        )

    # Update Next Steps if provided
    if next_steps:
        steps = [s.strip() for s in next_steps.split("|")]
        steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
        text = re.sub(
            r"(### Next Steps\n)(\d+\..*\n?)*",
            rf"\g<1>{steps_text}\n",
            text,
            count=1
        )

    write_text(context_path, text)
    print(f"✅ CONTEXT.md updated at {timestamp}")
    return 0


def run_summarize(ai_dir: Path) -> int:
    """Prepare all .ai files for AI summarization."""
    files_to_summarize = ["DECISIONS.md", "PATTERNS.md", "LESSONS.md", "TASKS.md", "REQUIREMENTS.md", "DESIGN.md", "TESTING.md", "RELEASE.md"]
    
    print("📝 AI: Please summarize these files into concise CONTEXT.md:")
    print()
    for fname in files_to_summarize:
        path = ai_dir / fname
        if path.exists():
            content = read_text(path)
            lines = content.splitlines()
            print(f"--- {fname} ({len(lines)} lines) ---")
            print(content)
            print()
        else:
            print(f"⚠️  {fname}: not found")
    
    print("═══════════════════════════════════════════")
    print("AI: Read the files above and update CONTEXT.md with:")
    print("  - Active decisions and rationale")
    print("  - Current patterns/conventions")
    print("  - Critical lessons to avoid")
    print("  - Task status (done/pending)")
    print("  - Requirements status")
    print("  - Design overview")
    print("  - Test coverage")
    print("  - Recent releases")
    print("═══════════════════════════════════════════")
    return 0


# --- SDLC commands ---

def run_add_requirement(ai_dir: Path, req_id: str, title: str, user_story: str, priority: str = "Medium", acceptance_criteria: str = "") -> int:
    """Add a new requirement to REQUIREMENTS.md."""
    req_path = ai_dir / "REQUIREMENTS.md"
    if not req_path.exists():
        write_text(req_path, DEFAULT_TEMPLATES["REQUIREMENTS.md"])

    date = datetime.now().strftime("%Y-%m-%d")
    criteria_lines = "\n".join(f"  - [ ] {c.strip()}" for c in acceptance_criteria.split("|")) if acceptance_criteria else "  - [ ] [Criterion 1]"

    entry = f"""### [{req_id}] {title}
- **Priority**: {priority}
- **Status**: Proposed
- **User Story**: {user_story}
- **Acceptance Criteria**:
{criteria_lines}
- **Date**: {date}
"""

    text = read_text(req_path)
    lines = text.splitlines()
    insert_idx = 1
    for i, line in enumerate(lines):
        if line.startswith("## ") or line.startswith("<!--"):
            insert_idx = i + 1
        elif line.strip() and not line.startswith("##") and not line.startswith("<!--"):
            break

    lines.insert(insert_idx, entry)
    write_text(req_path, "\n".join(lines).rstrip() + "\n")
    print(f"✅ Requirement [{req_id}] added: {title}")
    return 0


def run_requirement_done(ai_dir: Path, req_id: str, notes: str = "") -> int:
    """Mark a requirement as done."""
    req_path = ai_dir / "REQUIREMENTS.md"
    if not req_path.exists():
        print(f"⚠️  REQUIREMENTS.md not found")
        return 1

    text = read_text(req_path)
    # Update status to Done
    text = re.sub(
        rf"(### \[{re.escape(req_id)}\].*?-\s*\*\*Status\*\*:\s*)(Proposed|In Progress)",
        rf"\g<1>Done",
        text,
        flags=re.DOTALL
    )

    # Update acceptance criteria checkboxes
    req_block = re.search(rf"### \[{re.escape(req_id)}\].*?(?=### \[|$)", text, re.DOTALL)
    if req_block:
        block = req_block.group(0)
        updated_block = re.sub(r"- \[ \] ", "- [x] ", block)
        text = text.replace(block, updated_block)

    if notes:
        text = text.rstrip() + f"\n\n> **{req_id} Notes**: {notes}"

    write_text(req_path, text)
    print(f"✅ Requirement [{req_id}] marked as Done")
    return 0


def run_update_design(ai_dir: Path, section: str, content: str) -> int:
    """Update a section in DESIGN.md."""
    design_path = ai_dir / "DESIGN.md"
    if not design_path.exists():
        write_text(design_path, DEFAULT_TEMPLATES["DESIGN.md"])

    text = read_text(design_path)
    section_map = {
        "architecture": "### Architecture Overview",
        "backend": "### Backend Components",
        "frontend": "### Frontend / UI Components",
        "ui-patterns": "### UI/UX Patterns",
        "data-models": "### Data Models",
        "api": "### API Contracts",
        "state": "### State Management",
        "dependencies": "### External Dependencies",
    }

    section_header = section_map.get(section.lower(), section)
    
    # Check if section exists
    if section_header in text:
        # Replace content under section
        pattern = rf"({re.escape(section_header)}\n)(.*?)(?=###|$)"
        replacement = rf"\g<1>{content}\n\n"
        text = re.sub(pattern, replacement, text, flags=re.DOTALL, count=1)
    else:
        # Add new section
        text = text.rstrip() + f"\n\n{section_header}\n{content}\n"

    write_text(design_path, text)
    print(f"✅ DESIGN.md updated: {section}")
    return 0


def run_update_testing(ai_dir: Path, coverage_unit: str = "", coverage_integration: str = "", coverage_e2e: str = "", gaps: str = "", benchmarks: str = "") -> int:
    """Update TESTING.md with current status."""
    testing_path = ai_dir / "TESTING.md"
    if not testing_path.exists():
        write_text(testing_path, DEFAULT_TEMPLATES["TESTING.md"])

    text = read_text(testing_path)

    # Update coverage percentages
    if coverage_unit:
        text = re.sub(r"- Unit Tests: \[.*?\]%", f"- Unit Tests: {coverage_unit}%", text)
    if coverage_integration:
        text = re.sub(r"- Integration Tests: \[.*?\]%", f"- Integration Tests: {coverage_integration}%", text)
    if coverage_e2e:
        text = re.sub(r"- E2E Tests: \[.*?\]%", f"- E2E Tests: {coverage_e2e}%", text)

    # Update gaps
    if gaps:
        gaps_text = "\n".join(f"- {g.strip()}" for g in gaps.split("|"))
        text = re.sub(
            r"(### Known Test Gaps\n)(- .*\n?)*",
            rf"\g<1>{gaps_text}\n",
            text,
            flags=re.DOTALL
        )

    # Update benchmarks
    if benchmarks:
        bench_text = "\n".join(f"- {b.strip()}" for b in benchmarks.split("|"))
        text = re.sub(
            r"(### Performance Benchmarks\n)(- .*\n?)*",
            rf"\g<1>{bench_text}\n",
            text,
            flags=re.DOTALL
        )

    write_text(testing_path, text)
    print(f"✅ TESTING.md updated")
    return 0


def run_add_release(ai_dir: Path, version: str, added: str = "", changed: str = "", fixed: str = "", deployment: str = "") -> int:
    """Add a new release to RELEASE.md."""
    release_path = ai_dir / "RELEASE.md"
    if not release_path.exists():
        write_text(release_path, DEFAULT_TEMPLATES["RELEASE.md"])

    date = datetime.now().strftime("%Y-%m-%d")

    added_lines = "\n".join(f"- {a.strip()}" for a in added.split("|")) if added else "- [Feature]"
    changed_lines = "\n".join(f"- {c.strip()}" for c in changed.split("|")) if changed else ""
    fixed_lines = "\n".join(f"- {f.strip()}" for f in fixed.split("|")) if fixed else ""
    deployment_lines = "\n".join(f"- {d.strip()}" for d in deployment.split("|")) if deployment else ""

    entry = f"""### [{version}] - {date}
#### Added
{added_lines}
#### Changed
{changed_lines}
#### Fixed
{fixed_lines}
#### Deployment
{deployment_lines}
"""

    text = read_text(release_path)
    # Insert after header
    lines = text.splitlines()
    insert_idx = 1
    for i, line in enumerate(lines):
        if line.startswith("## ") or line.startswith("<!--"):
            insert_idx = i + 1
        elif line.strip() and not line.startswith("##") and not line.startswith("<!--"):
            break

    lines.insert(insert_idx, entry)
    write_text(release_path, "\n".join(lines).rstrip() + "\n")
    print(f"✅ Release [{version}] added")
    return 0


def run_task_done(ai_dir: Path, task: str) -> int:
    """Mark a task as done in TASKS.md."""
    tasks_path = ai_dir / "TASKS.md"
    if not tasks_path.exists():
        write_text(tasks_path, DEFAULT_TEMPLATES["TASKS.md"])

    text = read_text(tasks_path)
    date = datetime.now().strftime("%Y-%m-%d")

    # Check if task exists and mark it done
    if re.search(rf"- \[ \] .*{re.escape(task)}", text):
        text = re.sub(
            rf"(- \[ \] .*)({re.escape(task)}.*)",
            rf"- [x] \2 ({date})",
            text
        )
        print(f"✅ Task marked done: {task}")
    else:
        # Add as new completed task
        entry = f"- [x] {task} ({date})"
        # Find Active Tasks section and add there
        text = re.sub(
            r"(## Active Tasks\n)",
            rf"\1{entry}\n",
            text,
            count=1
        )
        print(f"✅ Task added as done: {task}")

    write_text(tasks_path, text)
    return 0


def run_add_pattern(ai_dir: Path, category: str, title: str, description: str) -> int:
    """Add a new pattern to PATTERNS.md."""
    patterns_path = ai_dir / "PATTERNS.md"
    if not patterns_path.exists():
        write_text(patterns_path, DEFAULT_TEMPLATES["PATTERNS.md"])

    text = read_text(patterns_path)

    # Check if category section exists
    category_header = f"### {category}"
    if category_header in text:
        # Add under existing category
        entry = f"\n#### {title}\n{description}\n"
        text = re.sub(
            rf"({re.escape(category_header)}\n)",
            rf"\1{entry}",
            text,
            count=1
        )
    else:
        # Create new category section
        entry = f"\n{category_header}\n\n#### {title}\n{description}\n"
        # Add before the last section or at the end
        text = text.rstrip() + "\n" + entry

    write_text(patterns_path, text)
    print(f"✅ Pattern added: {title} (category: {category})")
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

    # Update commands
    p_decision = sub.add_parser("add-decision", help="Add a new architecture decision.")
    p_decision.add_argument("title", type=str, help="Decision title")
    p_decision.add_argument("--context", required=True, help="Why this decision was needed")
    p_decision.add_argument("--decision", required=True, help="What was decided")
    p_decision.add_argument("--consequences", required=True, help="Trade-offs and implications")
    p_decision.add_argument("--status", default="Proposed", help="Decision status (default: Proposed)")

    p_lesson = sub.add_parser("add-lesson", help="Add a new lesson learned.")
    p_lesson.add_argument("title", type=str, help="Lesson title")
    p_lesson.add_argument("--symptom", required=True, help="What went wrong")
    p_lesson.add_argument("--root-cause", required=True, help="Why it happened")
    p_lesson.add_argument("--fix", required=True, help="How it was resolved")
    p_lesson.add_argument("--prevention", required=True, help="How to avoid it in future")

    p_context = sub.add_parser("update-context", help="Update CONTEXT.md with recent changes.")
    p_context.add_argument("--change", type=str, help="Description of recent change")
    p_context.add_argument("--context", type=str, help="Current context/background")
    p_context.add_argument("--blocker", type=str, help="Current blocker")
    p_context.add_argument("--next-steps", type=str, help="Next steps (pipe-separated for multiple)")

    p_task = sub.add_parser("task-done", help="Mark a task as completed in TASKS.md.")
    p_task.add_argument("task", type=str, help="Task description")

    p_pattern = sub.add_parser("add-pattern", help="Add a new code pattern.")
    p_pattern.add_argument("category", type=str, help="Pattern category (e.g., 'Structure', 'Naming')")
    p_pattern.add_argument("title", type=str, help="Pattern title")
    p_pattern.add_argument("description", type=str, help="Pattern description")

    p_summarize = sub.add_parser("summarize", help="Display all .ai files for AI to summarize into CONTEXT.md.")

    # SDLC commands
    p_req = sub.add_parser("add-requirement", help="Add a new requirement.")
    p_req.add_argument("req_id", type=str, help="Requirement ID (e.g., REQ-001)")
    p_req.add_argument("title", type=str, help="Requirement title")
    p_req.add_argument("--user-story", required=True, help="As a [user], I want [goal] so that [benefit]")
    p_req.add_argument("--priority", default="Medium", help="High, Medium, Low (default: Medium)")
    p_req.add_argument("--acceptance", default="", help="Acceptance criteria (pipe-separated)")

    p_req_done = sub.add_parser("requirement-done", help="Mark a requirement as done.")
    p_req_done.add_argument("req_id", type=str, help="Requirement ID")
    p_req_done.add_argument("--notes", default="", help="Implementation notes")

    p_design = sub.add_parser("update-design", help="Update DESIGN.md section.")
    p_design.add_argument("section", type=str, help="Section: architecture|backend|frontend|ui-patterns|data-models|api|state|dependencies")
    p_design.add_argument("content", type=str, help="Section content (markdown)")

    p_testing = sub.add_parser("update-testing", help="Update TESTING.md with current status.")
    p_testing.add_argument("--unit", type=str, help="Unit test coverage %")
    p_testing.add_argument("--integration", type=str, help="Integration test coverage %")
    p_testing.add_argument("--e2e", type=str, help="E2E test coverage %")
    p_testing.add_argument("--gaps", type=str, help="Known test gaps (pipe-separated)")
    p_testing.add_argument("--benchmarks", type=str, help="Performance benchmarks (pipe-separated)")

    p_release = sub.add_parser("add-release", help="Add a new release to RELEASE.md.")
    p_release.add_argument("version", type=str, help="Version (e.g., v0.1.0)")
    p_release.add_argument("--added", type=str, help="New features (pipe-separated)")
    p_release.add_argument("--changed", type=str, help="Changed behavior (pipe-separated)")
    p_release.add_argument("--fixed", type=str, help="Bug fixes (pipe-separated)")
    p_release.add_argument("--deployment", type=str, help="Deployment notes (pipe-separated)")

    return parser


# --- Main ---

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    ai_dir = root / ".ai"

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

    # Update commands
    if args.command == "add-decision":
        return run_add_decision(
            ai_dir,
            title=args.title,
            context=args.context,
            decision=args.decision,
            consequences=args.consequences,
            status=args.status,
        )
    if args.command == "add-lesson":
        return run_add_lesson(
            ai_dir,
            title=args.title,
            symptom=args.symptom,
            root_cause=args.root_cause,
            fix=args.fix,
            prevention=args.prevention,
        )
    if args.command == "update-context":
        return run_update_context(
            ai_dir,
            change=args.change or "",
            context=args.context or "",
            blocker=args.blocker or "",
            next_steps=args.next_steps or "",
        )
    if args.command == "task-done":
        return run_task_done(ai_dir, task=args.task)
    if args.command == "add-pattern":
        return run_add_pattern(
            ai_dir,
            category=args.category,
            title=args.title,
            description=args.description,
        )
    if args.command == "summarize":
        return run_summarize(ai_dir)

    # SDLC commands
    if args.command == "add-requirement":
        return run_add_requirement(
            ai_dir,
            req_id=args.req_id,
            title=args.title,
            user_story=args.user_story,
            priority=args.priority,
            acceptance_criteria=args.acceptance or "",
        )
    if args.command == "requirement-done":
        return run_requirement_done(
            ai_dir,
            req_id=args.req_id,
            notes=args.notes or "",
        )
    if args.command == "update-design":
        return run_update_design(
            ai_dir,
            section=args.section,
            content=args.content,
        )
    if args.command == "update-testing":
        return run_update_testing(
            ai_dir,
            coverage_unit=args.unit or "",
            coverage_integration=args.integration or "",
            coverage_e2e=args.e2e or "",
            gaps=args.gaps or "",
            benchmarks=args.benchmarks or "",
        )
    if args.command == "add-release":
        return run_add_release(
            ai_dir,
            version=args.version,
            added=args.added or "",
            changed=args.changed or "",
            fixed=args.fixed or "",
            deployment=args.deployment or "",
        )

    parser.print_help()
    return 1


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    sys.exit(main())
