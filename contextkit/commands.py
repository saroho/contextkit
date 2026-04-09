"""Command implementations for contextkit."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .files import (
    CORE_FILES,
    DEFAULT_TEMPLATES,
    COMPRESSIBLE_FILES,
    read_text,
    write_text,
    ensure_structure,
    compact_markdown,
)

# --- Init ---

def run_init(root: Path, force: bool) -> int:
    """Create missing .ai files and archive structure."""
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


# --- Status ---

def run_status(root: Path) -> int:
    """Show missing core files and line counts."""
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
        char_count = len(read_text(p))
        print(f"  - {name}: {line_count} lines, {char_count} chars")
    if missing:
        print("Missing:")
        for name in missing:
            print(f"  - {name}")
    return 0


# --- Add Decision ---

def get_next_decision_number(ai_dir: Path) -> str:
    """Auto-increment decision number based on year."""
    decisions_path = ai_dir / "DECISIONS.md"
    text = read_text(decisions_path)
    pattern = r"\[(\d{4}-)?(\d+)\]"
    matches = re.findall(pattern, text)
    current_year = datetime.now().year

    if not matches:
        return f"{current_year}-001"

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
    lines = text.splitlines()
    insert_idx = 1
    for i, line in enumerate(lines):
        if line.startswith("## ") or line.startswith("<!--"):
            insert_idx = i + 1
        elif line.strip() and not line.startswith("##") and not line.startswith("<!--"):
            break

    lines.insert(insert_idx, entry)
    write_text(decisions_path, "\n".join(lines).rstrip() + "\n")
    print(f"[+] Decision [{num}] added: {title}")
    return 0


# --- Add Lesson ---

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
    print(f"[+] Lesson added: {title}")
    return 0


# --- Add Pattern ---

def run_add_pattern(ai_dir: Path, category: str, title: str, description: str) -> int:
    """Add a new code pattern."""
    patterns_path = ai_dir / "PATTERNS.md"
    if not patterns_path.exists():
        write_text(patterns_path, DEFAULT_TEMPLATES["PATTERNS.md"])

    text = read_text(patterns_path)

    category_header = f"### {category}"
    if category_header in text:
        entry = f"\n#### {title}\n{description}\n"
        text = re.sub(
            rf"({re.escape(category_header)}\n)",
            rf"\1{entry}",
            text,
            count=1
        )
    else:
        entry = f"\n{category_header}\n\n#### {title}\n{description}\n"
        text = text.rstrip() + "\n" + entry

    write_text(patterns_path, text)
    print(f"[+] Pattern added: {title} (category: {category})")
    return 0


# --- Task Done ---

def run_task_done(ai_dir: Path, task: str) -> int:
    """Mark a task as completed in TASKS.md."""
    tasks_path = ai_dir / "TASKS.md"
    if not tasks_path.exists():
        write_text(tasks_path, DEFAULT_TEMPLATES["TASKS.md"])

    text = read_text(tasks_path)
    date = datetime.now().strftime("%Y-%m-%d")

    if re.search(rf"- \[ \] .*{re.escape(task)}", text):
        text = re.sub(
            rf"(- \[ \] .*)({re.escape(task)}.*)",
            rf"- [x] \2 ({date})",
            text
        )
        print(f"[+] Task marked done: {task}")
    else:
        entry = f"- [x] {task} ({date})"
        text = re.sub(
            r"(## Active Tasks\n)",
            rf"\1{entry}\n",
            text,
            count=1
        )
        print(f"[+] Task added as done: {task}")

    write_text(tasks_path, text)
    return 0


# --- Update Context ---

def run_update_context(ai_dir: Path, change: str = "", context: str = "", blocker: str = "", next_steps: str = "") -> int:
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

    # Update Context section
    if context:
        # Find ### Context and replace until next ###
        text = re.sub(
            r"(### Context\n)([^\n]*\n)*?(?=###|\Z)",
            rf"\1{context}\n\n",
            text,
            flags=re.DOTALL
        )

    # Update Blockers
    if blocker:
        text = re.sub(
            r"(### Blockers\n)(- .*\n?)*",
            rf"\1- {blocker}\n",
            text,
            count=1
        )

    # Update Next Steps
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
    print(f"[+] CONTEXT.md updated at {timestamp}")
    return 0


# --- Add Requirement ---

def run_add_requirement(ai_dir: Path, req_id: str, title: str, user_story: str, priority: str = "Medium", acceptance_criteria: str = "") -> int:
    """Add a new requirement."""
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
    print(f"[+] Requirement [{req_id}] added: {title}")
    return 0


def run_requirement_done(ai_dir: Path, req_id: str, notes: str = "") -> int:
    """Mark a requirement as done."""
    req_path = ai_dir / "REQUIREMENTS.md"
    if not req_path.exists():
        print(f"WARNING: REQUIREMENTS.md not found")
        return 1

    text = read_text(req_path)
    text = re.sub(
        rf"(### \[{re.escape(req_id)}\].*?-\s*\*\*Status\*\*:\s*)(Proposed|In Progress)",
        rf"\g<1>Done",
        text,
        flags=re.DOTALL
    )

    req_block = re.search(rf"### \[{re.escape(req_id)}\].*?(?=### \[|$)", text, re.DOTALL)
    if req_block:
        block = req_block.group(0)
        updated_block = re.sub(r"- \[ \] ", "- [x] ", block)
        text = text.replace(block, updated_block)

    if notes:
        text = text.rstrip() + f"\n\n> **{req_id} Notes**: {notes}"

    write_text(req_path, text)
    print(f"[+] Requirement [{req_id}] marked as Done")
    return 0


# --- Update Design ---

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

    if section_header in text:
        pattern = rf"({re.escape(section_header)}\n)(.*?)(?=###|$)"
        replacement = rf"\g<1>{content}\n\n"
        text = re.sub(pattern, replacement, text, flags=re.DOTALL, count=1)
    else:
        text = text.rstrip() + f"\n\n{section_header}\n{content}\n"

    write_text(design_path, text)
    print(f"[+] DESIGN.md updated: {section}")
    return 0


# --- Update Testing ---

def run_update_testing(ai_dir: Path, coverage_unit: str = "", coverage_integration: str = "", coverage_e2e: str = "", gaps: str = "", benchmarks: str = "") -> int:
    """Update TESTING.md with current status."""
    testing_path = ai_dir / "TESTING.md"
    if not testing_path.exists():
        write_text(testing_path, DEFAULT_TEMPLATES["TESTING.md"])

    text = read_text(testing_path)

    if coverage_unit:
        text = re.sub(r"- Unit Tests: \[.*?\]%", f"- Unit Tests: {coverage_unit}%", text)
    if coverage_integration:
        text = re.sub(r"- Integration Tests: \[.*?\]%", f"- Integration Tests: {coverage_integration}%", text)
    if coverage_e2e:
        text = re.sub(r"- E2E Tests: \[.*?\]%", f"- E2E Tests: {coverage_e2e}%", text)

    if gaps:
        gaps_text = "\n".join(f"- {g.strip()}" for g in gaps.split("|"))
        text = re.sub(
            r"(### Known Test Gaps\n)(- .*\n?)*",
            rf"\g<1>{gaps_text}\n",
            text,
            flags=re.DOTALL
        )

    if benchmarks:
        bench_text = "\n".join(f"- {b.strip()}" for b in benchmarks.split("|"))
        text = re.sub(
            r"(### Performance Benchmarks\n)(- .*\n?)*",
            rf"\g<1>{bench_text}\n",
            text,
            flags=re.DOTALL
        )

    write_text(testing_path, text)
    print(f"[+] TESTING.md updated")
    return 0


# --- Add Release ---

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
    lines = text.splitlines()
    insert_idx = 1
    for i, line in enumerate(lines):
        if line.startswith("## ") or line.startswith("<!--"):
            insert_idx = i + 1
        elif line.strip() and not line.startswith("##") and not line.startswith("<!--"):
            break

    lines.insert(insert_idx, entry)
    write_text(release_path, "\n".join(lines).rstrip() + "\n")
    print(f"[+] Release [{version}] added")
    return 0
