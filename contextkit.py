#!/usr/bin/env python3
"""Single-file tool to bootstrap and maintain the .ai memory system."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import sys
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

PLAN_VERSION = 1
PLAN_SCHEMA_FILE = "maintain-plan.schema.json"
METRICS_FILE = "metrics.json"


@dataclass
class SafetyCaps:
    max_files_rotated: int
    max_total_lines_removed: int
    max_archive_chars_added: int


@dataclass
class ExecutionOptions:
    dry_run: bool
    explain: bool
    deterministic: bool
    min_confidence: float


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
    ensure_plan_schema_file(root, summary)


def rotate_large_files(
    root: Path,
    line_threshold: int,
    keep_last: int,
    summary: Summary,
) -> None:
    plan = default_maintain_plan(
        line_threshold=line_threshold,
        keep_last=keep_last,
        task_days=30,
        caps=SafetyCaps(max_files_rotated=999, max_total_lines_removed=10**9, max_archive_chars_added=10**9),
    )
    plan["tasks"]["enabled"] = False
    execute_plan(
        root=root,
        plan=plan,
        summary=summary,
        options=ExecutionOptions(dry_run=False, explain=False, deterministic=False, min_confidence=0.0),
        caps=SafetyCaps(max_files_rotated=999, max_total_lines_removed=10**9, max_archive_chars_added=10**9),
    )


def rotate_file_if_needed(
    ai_dir: Path,
    file_name: str,
    line_threshold: int,
    keep_last: int,
    now_token: str,
    summary: Summary,
) -> None:
    archive_key = FILE_TO_ARCHIVE[file_name]
    file_path = ai_dir / file_name
    if not file_path.exists():
        return
    lines = read_text(file_path).splitlines()
    if len(lines) <= line_threshold:
        return
    archive_path = ai_dir / "archive" / archive_key / f"{file_path.stem}_{now_token}.md"
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


def parse_iso_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def build_llm_plan_input(root: Path) -> dict:
    ai_dir = root / ".ai"
    today = datetime.now().date()
    completed_line = re.compile(r"^- \[x\].*?(\d{4}-\d{2}-\d{2})")

    files: dict[str, dict[str, int | bool]] = {}
    for file_name in CORE_FILES:
        path = ai_dir / file_name
        lines = read_text(path).splitlines() if path.exists() else []
        files[file_name] = {"exists": path.exists(), "line_count": len(lines)}

    completed_tasks: list[dict[str, int | str]] = []
    tasks_path = ai_dir / "TASKS.md"
    if tasks_path.exists():
        for line in read_text(tasks_path).splitlines():
            match = completed_line.search(line)
            if not match:
                continue
            dt = parse_iso_date(match.group(1))
            if not dt:
                continue
            age = (today - dt.date()).days
            completed_tasks.append({"date": match.group(1), "age_days": age, "line": line})

    return {
        "version": PLAN_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(root),
        "ai_exists": ai_dir.exists(),
        "files": files,
        "completed_tasks": completed_tasks,
        "defaults": {
            "line_threshold": 100,
            "keep_last": 60,
            "task_days": 30,
            "allowed_rotate_files": list(FILE_TO_ARCHIVE.keys()),
            "default_confidence": 0.8,
        },
        "metrics": load_metrics(root),
        "schema_file": str((ai_dir / PLAN_SCHEMA_FILE).resolve()),
        "examples": {
            "good_plan": build_good_plan_example(),
            "bad_plan": build_bad_plan_example(),
        },
        "instructions": [
            "Create a JSON plan compatible with `contextkit.py maintain --plan-file <file>`.",
            "Use only file names from defaults.allowed_rotate_files.",
            "Set confidence from 0.0 to 1.0 and include a short reason.",
            "Respect safety caps to avoid large accidental changes.",
        ],
    }


def build_plan_template() -> dict:
    return {
        "version": PLAN_VERSION,
        "rotate": [
            {
                "file": "CONTEXT.md",
                "line_threshold": 120,
                "keep_last": 80,
                "confidence": 0.9,
                "reason": "High churn file, keep recent context only.",
            },
            {
                "file": "DECISIONS.md",
                "line_threshold": 220,
                "keep_last": 140,
                "confidence": 0.7,
                "reason": "Archive only when decision history is too large.",
            },
            {
                "file": "LESSONS.md",
                "line_threshold": 180,
                "keep_last": 110,
                "confidence": 0.8,
                "reason": "Keep recent lessons quickly accessible.",
            },
        ],
        "tasks": {
            "enabled": True,
            "days": 45,
            "confidence": 0.85,
            "reason": "Completed tasks older than 45 days are usually low signal.",
        },
        "limits": {
            "max_files_rotated": 3,
            "max_total_lines_removed": 500,
            "max_archive_chars_added": 120000,
        },
    }


def merge_template_with_defaults(template: dict, defaults: dict) -> dict:
    merged = json.loads(json.dumps(template))
    existing_files = set()
    for item in merged.get("rotate", []):
        file_name = item.get("file")
        if isinstance(file_name, str):
            existing_files.add(file_name)
    for item in defaults.get("rotate", []):
        file_name = item.get("file")
        if isinstance(file_name, str) and file_name not in existing_files:
            merged.setdefault("rotate", []).append(item)
    if "tasks" not in merged:
        merged["tasks"] = defaults.get("tasks", {})
    default_limits = defaults.get("limits", {})
    merged_limits = merged.get("limits", {})
    if not isinstance(merged_limits, dict):
        merged_limits = {}
    for key, value in default_limits.items():
        if key not in merged_limits:
            merged_limits[key] = value
    merged["limits"] = merged_limits
    merged["version"] = PLAN_VERSION
    return merged


def build_good_plan_example() -> dict:
    return {
        "version": PLAN_VERSION,
        "rotate": [
            {
                "file": "CONTEXT.md",
                "line_threshold": 130,
                "keep_last": 80,
                "confidence": 0.92,
                "reason": "Context grows quickly and recent lines are most relevant.",
            }
        ],
        "tasks": {
            "enabled": True,
            "days": 40,
            "confidence": 0.9,
            "reason": "Old completed tasks are archived after 40 days.",
        },
        "limits": {
            "max_files_rotated": 2,
            "max_total_lines_removed": 250,
            "max_archive_chars_added": 60000,
        },
    }


def build_bad_plan_example() -> dict:
    return {
        "version": PLAN_VERSION,
        "rotate": [
            {
                "file": ".env",
                "line_threshold": -5,
                "keep_last": -10,
                "confidence": 1.2,
                "reason": "",
            }
        ],
        "tasks": {"enabled": "yes", "days": -30},
    }


def build_plan_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://contextkit.local/maintain-plan.schema.json",
        "title": "ContextKit Maintain Plan",
        "type": "object",
        "required": ["version", "rotate", "tasks"],
        "additionalProperties": False,
        "properties": {
            "version": {"type": "integer", "const": PLAN_VERSION},
            "rotate": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["file", "line_threshold", "keep_last"],
                    "properties": {
                        "file": {"type": "string", "enum": list(FILE_TO_ARCHIVE.keys())},
                        "line_threshold": {"type": "integer", "minimum": 1},
                        "keep_last": {"type": "integer", "minimum": 0},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "reason": {"type": "string", "minLength": 1},
                    },
                },
            },
            "tasks": {
                "type": "object",
                "additionalProperties": False,
                "required": ["enabled", "days"],
                "properties": {
                    "enabled": {"type": "boolean"},
                    "days": {"type": "integer", "minimum": 0},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "reason": {"type": "string", "minLength": 1},
                },
            },
            "limits": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "max_files_rotated": {"type": "integer", "minimum": 0},
                    "max_total_lines_removed": {"type": "integer", "minimum": 0},
                    "max_archive_chars_added": {"type": "integer", "minimum": 0},
                },
            },
        },
    }


def ensure_plan_schema_file(root: Path, summary: Summary) -> Path:
    ai_dir = ensure_structure(root, summary)
    path = ai_dir / PLAN_SCHEMA_FILE
    content = json.dumps(build_plan_schema(), indent=2) + "\n"
    if read_text(path) != content:
        write_text(path, content)
        if path.exists():
            if str(path) not in summary.updated:
                summary.updated.append(str(path))
    return path


def default_metrics() -> dict[str, int]:
    return {
        "plans_validated": 0,
        "plans_rejected": 0,
        "fallback_used": 0,
    }


def load_metrics(root: Path) -> dict[str, int]:
    metrics_path = root / ".ai" / "archive" / METRICS_FILE
    if not metrics_path.exists():
        return default_metrics()
    try:
        data = json.loads(read_text(metrics_path))
    except json.JSONDecodeError:
        return default_metrics()
    out = default_metrics()
    for key in out:
        value = data.get(key, 0)
        if isinstance(value, int) and value >= 0:
            out[key] = value
    return out


def save_metrics(root: Path, summary: Summary, metrics: dict[str, int]) -> None:
    ai_dir = ensure_structure(root, summary)
    metrics_path = ai_dir / "archive" / METRICS_FILE
    write_text(metrics_path, json.dumps(metrics, indent=2) + "\n")
    if str(metrics_path) not in summary.updated:
        summary.updated.append(str(metrics_path))


def load_and_validate_plan(plan_path: Path) -> dict:
    if not plan_path.exists():
        raise ValueError(f"Plan file not found: {plan_path}")

    try:
        raw = json.loads(read_text(plan_path))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid JSON in plan file: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("Plan must be a JSON object.")
    if raw.get("version", PLAN_VERSION) != PLAN_VERSION:
        raise ValueError(f"Unsupported plan version. Expected version {PLAN_VERSION}.")

    rotate_raw = raw.get("rotate", [])
    if rotate_raw is None:
        rotate_raw = []
    if not isinstance(rotate_raw, list):
        raise ValueError("`rotate` must be a list.")

    seen_files: set[str] = set()
    rotate: list[dict[str, int | str | float]] = []
    for idx, item in enumerate(rotate_raw):
        if not isinstance(item, dict):
            raise ValueError(f"`rotate[{idx}]` must be an object.")
        file_name = item.get("file")
        if not isinstance(file_name, str) or file_name not in FILE_TO_ARCHIVE:
            raise ValueError(f"`rotate[{idx}].file` must be one of: {', '.join(FILE_TO_ARCHIVE)}")
        if file_name in seen_files:
            raise ValueError(f"Duplicate rotate rule for file: {file_name}")
        seen_files.add(file_name)

        line_threshold = item.get("line_threshold")
        keep_last = item.get("keep_last")
        if not isinstance(line_threshold, int) or line_threshold <= 0:
            raise ValueError(f"`rotate[{idx}].line_threshold` must be a positive integer.")
        if not isinstance(keep_last, int) or keep_last < 0:
            raise ValueError(f"`rotate[{idx}].keep_last` must be a non-negative integer.")

        confidence = item.get("confidence", 1.0)
        reason = item.get("reason", "Rule derived from model context.")
        if not isinstance(confidence, (int, float)) or confidence < 0.0 or confidence > 1.0:
            raise ValueError(f"`rotate[{idx}].confidence` must be between 0.0 and 1.0.")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"`rotate[{idx}].reason` must be a non-empty string.")

        rotate.append(
            {
                "file": file_name,
                "line_threshold": line_threshold,
                "keep_last": keep_last,
                "confidence": float(confidence),
                "reason": reason.strip(),
            }
        )

    tasks_raw = raw.get("tasks", {"enabled": True, "days": 30, "confidence": 1.0, "reason": "Default task archival."})
    if not isinstance(tasks_raw, dict):
        raise ValueError("`tasks` must be an object.")
    enabled = tasks_raw.get("enabled", True)
    days = tasks_raw.get("days", 30)
    tasks_confidence = tasks_raw.get("confidence", 1.0)
    tasks_reason = tasks_raw.get("reason", "Default task archival.")
    if not isinstance(enabled, bool):
        raise ValueError("`tasks.enabled` must be true or false.")
    if not isinstance(days, int) or days < 0:
        raise ValueError("`tasks.days` must be a non-negative integer.")
    if not isinstance(tasks_confidence, (int, float)) or tasks_confidence < 0.0 or tasks_confidence > 1.0:
        raise ValueError("`tasks.confidence` must be between 0.0 and 1.0.")
    if not isinstance(tasks_reason, str) or not tasks_reason.strip():
        raise ValueError("`tasks.reason` must be a non-empty string.")

    limits_raw = raw.get("limits", {})
    if not isinstance(limits_raw, dict):
        raise ValueError("`limits` must be an object when provided.")
    limits: dict[str, int] = {}
    for key in ("max_files_rotated", "max_total_lines_removed", "max_archive_chars_added"):
        if key in limits_raw:
            value = limits_raw[key]
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"`limits.{key}` must be a non-negative integer.")
            limits[key] = value

    return {
        "version": PLAN_VERSION,
        "rotate": rotate,
        "tasks": {
            "enabled": enabled,
            "days": days,
            "confidence": float(tasks_confidence),
            "reason": tasks_reason.strip(),
        },
        "limits": limits,
    }


def default_maintain_plan(line_threshold: int, keep_last: int, task_days: int, caps: SafetyCaps) -> dict:
    rotate = []
    for name in sorted(FILE_TO_ARCHIVE):
        rotate.append(
            {
                "file": name,
                "line_threshold": line_threshold,
                "keep_last": keep_last,
                "confidence": 1.0,
                "reason": "Deterministic default threshold.",
            }
        )
    return {
        "version": PLAN_VERSION,
        "rotate": rotate,
        "tasks": {
            "enabled": True,
            "days": task_days,
            "confidence": 1.0,
            "reason": "Deterministic default task archival.",
        },
        "limits": {
            "max_files_rotated": caps.max_files_rotated,
            "max_total_lines_removed": caps.max_total_lines_removed,
            "max_archive_chars_added": caps.max_archive_chars_added,
        },
    }


def effective_caps(base: SafetyCaps, plan_limits: dict[str, Any]) -> SafetyCaps:
    return SafetyCaps(
        max_files_rotated=min(base.max_files_rotated, int(plan_limits.get("max_files_rotated", base.max_files_rotated))),
        max_total_lines_removed=min(
            base.max_total_lines_removed,
            int(plan_limits.get("max_total_lines_removed", base.max_total_lines_removed)),
        ),
        max_archive_chars_added=min(
            base.max_archive_chars_added,
            int(plan_limits.get("max_archive_chars_added", base.max_archive_chars_added)),
        ),
    )


def inspect_rotate_operation(ai_dir: Path, file_name: str, line_threshold: int, keep_last: int, now_token: str) -> dict | None:
    file_path = ai_dir / file_name
    if not file_path.exists():
        return None
    lines = read_text(file_path).splitlines()
    line_count = len(lines)
    if line_count <= line_threshold:
        return None
    kept = lines[-keep_last:] if keep_last > 0 else []
    archive_path = ai_dir / "archive" / FILE_TO_ARCHIVE[file_name] / f"{file_path.stem}_{now_token}.md"
    archive_text = "\n".join(lines).strip() + "\n"
    updated_text = ("\n".join(kept)).strip() + ("\n" if kept else "")
    return {
        "type": "rotate",
        "file": file_name,
        "file_path": file_path,
        "archive_path": archive_path,
        "line_count": line_count,
        "line_threshold": line_threshold,
        "keep_last": keep_last,
        "kept_lines": len(kept),
        "removed_lines": max(0, line_count - len(kept)),
        "archive_chars_added": len(archive_text),
        "archive_text": archive_text,
        "updated_text": updated_text,
    }


def inspect_task_archive_operation(ai_dir: Path, days: int, now_token: str) -> dict | None:
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
        done_date = parse_iso_date(match.group(1))
        if not done_date:
            keep.append(line)
            continue
        if (today - done_date.date()).days > days:
            to_archive.append(line)
        else:
            keep.append(line)

    if not to_archive:
        return None

    archive_path = ai_dir / "archive" / "tasks" / f"TASKS_completed_{now_token[:8]}.md"
    previous = read_text(archive_path)
    appended = "\n".join(to_archive) + "\n"
    combined = (previous.strip() + "\n" if previous.strip() else "") + appended
    updated_text = "\n".join(keep).rstrip() + "\n"
    archive_growth = len(combined) - len(previous)

    return {
        "type": "tasks",
        "tasks_path": tasks_path,
        "archive_path": archive_path,
        "days": days,
        "removed_lines": len(to_archive),
        "archive_chars_added": max(0, archive_growth),
        "to_archive": to_archive,
        "combined_archive_text": combined,
        "updated_text": updated_text,
    }


def collect_operations(
    root: Path,
    plan: dict,
    options: ExecutionOptions,
) -> tuple[list[dict], dict | None, list[str]]:
    ai_dir = ensure_structure(root, Summary())
    now_token = datetime.now().strftime("%Y%m%d_%H%M%S")
    rotate_ops: list[dict] = []
    skipped: list[str] = []

    for rule in plan["rotate"]:
        confidence = float(rule["confidence"])
        if confidence < options.min_confidence:
            skipped.append(
                f"skip rotate {rule['file']} confidence={confidence:.2f} below min={options.min_confidence:.2f}"
            )
            continue
        op = inspect_rotate_operation(
            ai_dir=ai_dir,
            file_name=str(rule["file"]),
            line_threshold=int(rule["line_threshold"]),
            keep_last=int(rule["keep_last"]),
            now_token=now_token,
        )
        if op:
            op["reason"] = str(rule["reason"])
            op["confidence"] = confidence
            rotate_ops.append(op)

    tasks_op = None
    tasks = plan["tasks"]
    if bool(tasks["enabled"]):
        confidence = float(tasks["confidence"])
        if confidence < options.min_confidence:
            skipped.append(
                f"skip tasks confidence={confidence:.2f} below min={options.min_confidence:.2f}"
            )
        else:
            tasks_op = inspect_task_archive_operation(
                ai_dir=ai_dir,
                days=int(tasks["days"]),
                now_token=now_token,
            )
            if tasks_op:
                tasks_op["reason"] = str(tasks["reason"])
                tasks_op["confidence"] = confidence

    if options.deterministic:
        rotate_ops = sorted(rotate_ops, key=lambda x: str(x["file"]))
    return rotate_ops, tasks_op, skipped


def enforce_caps(rotate_ops: list[dict], tasks_op: dict | None, caps: SafetyCaps) -> None:
    files_rotated = len(rotate_ops)
    removed_lines = sum(int(op["removed_lines"]) for op in rotate_ops)
    archive_chars = sum(int(op["archive_chars_added"]) for op in rotate_ops)
    if tasks_op:
        removed_lines += int(tasks_op["removed_lines"])
        archive_chars += int(tasks_op["archive_chars_added"])

    if files_rotated > caps.max_files_rotated:
        raise ValueError(
            f"Safety cap exceeded: files rotated {files_rotated} > max_files_rotated {caps.max_files_rotated}"
        )
    if removed_lines > caps.max_total_lines_removed:
        raise ValueError(
            "Safety cap exceeded: total lines removed "
            f"{removed_lines} > max_total_lines_removed {caps.max_total_lines_removed}"
        )
    if archive_chars > caps.max_archive_chars_added:
        raise ValueError(
            "Safety cap exceeded: archive chars added "
            f"{archive_chars} > max_archive_chars_added {caps.max_archive_chars_added}"
        )


def execute_operations(rotate_ops: list[dict], tasks_op: dict | None, summary: Summary, dry_run: bool) -> None:
    if dry_run:
        return
    for op in rotate_ops:
        write_text(Path(op["archive_path"]), str(op["archive_text"]))
        write_text(Path(op["file_path"]), str(op["updated_text"]))
        summary.archived.append(str(op["archive_path"]))
        summary.updated.append(str(op["file_path"]))
    if tasks_op:
        write_text(Path(tasks_op["archive_path"]), str(tasks_op["combined_archive_text"]))
        write_text(Path(tasks_op["tasks_path"]), str(tasks_op["updated_text"]))
        summary.archived.append(str(tasks_op["archive_path"]))
        summary.updated.append(str(tasks_op["tasks_path"]))


def print_execution_details(
    rotate_ops: list[dict],
    tasks_op: dict | None,
    skipped: list[str],
    dry_run: bool,
    explain: bool,
) -> None:
    if dry_run:
        print("Dry-run mode: no files will be modified.")
    if explain:
        for op in rotate_ops:
            print(
                "Rotate "
                f"{op['file']} lines={op['line_count']} threshold={op['line_threshold']} "
                f"keep_last={op['keep_last']} removed={op['removed_lines']} "
                f"confidence={op['confidence']:.2f} reason={op['reason']}"
            )
        if tasks_op:
            print(
                "Archive tasks "
                f"days={tasks_op['days']} removed={tasks_op['removed_lines']} "
                f"confidence={tasks_op['confidence']:.2f} reason={tasks_op['reason']}"
            )
        for line in skipped:
            print(f"Plan note: {line}")
    if not rotate_ops and not tasks_op and not skipped:
        print("Nothing to do.")


def archive_accepted_plan(root: Path, plan: dict, source_path: Path, summary: Summary) -> None:
    ai_dir = ensure_structure(root, summary)
    plans_dir = ai_dir / "archive" / "plans"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = plans_dir / f"maintain_plan_{stamp}.json"
    payload = {
        "accepted_at": datetime.now().isoformat(timespec="seconds"),
        "source_plan_file": str(source_path),
        "plan": plan,
    }
    write_text(archive_path, json.dumps(payload, indent=2) + "\n")
    summary.archived.append(str(archive_path))


def execute_plan(
    root: Path,
    plan: dict,
    summary: Summary,
    options: ExecutionOptions,
    caps: SafetyCaps,
) -> None:
    rotate_ops, tasks_op, skipped = collect_operations(root, plan, options)
    effective = effective_caps(caps, plan.get("limits", {}))
    enforce_caps(rotate_ops, tasks_op, effective)
    print_execution_details(rotate_ops, tasks_op, skipped, options.dry_run, options.explain)
    execute_operations(rotate_ops, tasks_op, summary, options.dry_run)


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


def run_init(root: Path, force: bool, summary: Summary) -> int:
    init_files(root, force=force, summary=summary)
    print_summary(summary)
    return 0


def run_maintain(
    root: Path,
    line_threshold: int,
    keep_last: int,
    task_days: int,
    plan_file: str | None,
    dry_run: bool,
    explain: bool,
    deterministic: bool,
    min_confidence: float,
    max_files_rotated: int,
    max_lines_removed: int,
    max_archive_chars: int,
    no_fallback: bool,
    summary: Summary,
) -> int:
    ensure_plan_schema_file(root, summary)
    metrics = load_metrics(root)
    caps = SafetyCaps(
        max_files_rotated=max_files_rotated,
        max_total_lines_removed=max_lines_removed,
        max_archive_chars_added=max_archive_chars,
    )
    options = ExecutionOptions(
        dry_run=dry_run,
        explain=explain,
        deterministic=deterministic,
        min_confidence=min_confidence,
    )

    if not plan_file:
        plan = default_maintain_plan(line_threshold, keep_last, task_days, caps)
        execute_plan(root=root, plan=plan, summary=summary, options=options, caps=caps)
        print_summary(summary)
        save_metrics(root, summary, metrics)
        return 0

    source_plan_path = Path(plan_file).resolve()
    try:
        plan = load_and_validate_plan(source_plan_path)
        metrics["plans_validated"] += 1
    except ValueError as exc:
        metrics["plans_rejected"] += 1
        print(f"Plan validation failed: {exc}", file=sys.stderr)
        if no_fallback:
            save_metrics(root, summary, metrics)
            return 2
        print("Falling back to deterministic defaults.", file=sys.stderr)
        metrics["fallback_used"] += 1
        plan = default_maintain_plan(line_threshold, keep_last, task_days, caps)

    execute_plan(root=root, plan=plan, summary=summary, options=options, caps=caps)
    if plan_file and not dry_run:
        archive_accepted_plan(root, plan, source_plan_path, summary)
    print_summary(summary)
    save_metrics(root, summary, metrics)
    return 0


def run_plan_check(
    root: Path,
    plan_file: str,
    min_confidence: float,
    deterministic: bool,
    max_files_rotated: int,
    max_lines_removed: int,
    max_archive_chars: int,
) -> int:
    plan = load_and_validate_plan(Path(plan_file).resolve())
    caps = SafetyCaps(
        max_files_rotated=max_files_rotated,
        max_total_lines_removed=max_lines_removed,
        max_archive_chars_added=max_archive_chars,
    )
    options = ExecutionOptions(
        dry_run=True,
        explain=True,
        deterministic=deterministic,
        min_confidence=min_confidence,
    )
    rotate_ops, tasks_op, skipped = collect_operations(root, plan, options)
    enforce_caps(rotate_ops, tasks_op, effective_caps(caps, plan.get("limits", {})))
    print("Plan check passed.")
    print_execution_details(rotate_ops, tasks_op, skipped, dry_run=True, explain=True)
    return 0


def run_llm_prompt(root: Path) -> int:
    input_payload = build_llm_plan_input(root)
    template = build_plan_template()
    schema = build_plan_schema()
    prompt = f"""You are generating a ContextKit maintain plan.

Rules:
- Output JSON only.
- Must satisfy the schema below.
- Use confidence [0.0, 1.0] and a concise reason for each rule.
- Keep archive operations conservative and within limits.

Schema:
{json.dumps(schema, indent=2)}

Input:
{json.dumps(input_payload, indent=2)}

Template:
{json.dumps(template, indent=2)}

Return ONLY the final JSON plan."""
    print(prompt)
    return 0


def run_plan_schema(root: Path, summary: Summary) -> int:
    path = ensure_plan_schema_file(root, summary)
    print(f"Wrote schema to: {path}")
    print(json.dumps(build_plan_schema(), indent=2))
    print_summary(summary)
    return 0


def run_plan_init(root: Path, output: str, force: bool, summary: Summary) -> int:
    ensure_plan_schema_file(root, summary)
    caps = SafetyCaps(
        max_files_rotated=5,
        max_total_lines_removed=1200,
        max_archive_chars_added=250000,
    )
    defaults = default_maintain_plan(
        line_threshold=100,
        keep_last=60,
        task_days=30,
        caps=caps,
    )
    merged = merge_template_with_defaults(build_plan_template(), defaults)
    out_path = (root / output).resolve() if not Path(output).is_absolute() else Path(output).resolve()
    if out_path.exists() and not force:
        summary.skipped.append(str(out_path))
        print(f"Plan file already exists: {out_path}")
        print("Use --force to overwrite.")
        print_summary(summary)
        return 0
    write_text(out_path, json.dumps(merged, indent=2) + "\n")
    if out_path.exists():
        summary.created.append(str(out_path))
    print(f"Wrote plan file: {out_path}")
    print_summary(summary)
    return 0


def run_plan_template() -> int:
    print(json.dumps(build_plan_template(), indent=2))
    return 0


def run_llm_plan_input(root: Path) -> int:
    print(json.dumps(build_llm_plan_input(root), indent=2))
    return 0


def run_all(
    root: Path,
    force: bool,
    line_threshold: int,
    keep_last: int,
    task_days: int,
    dry_run: bool,
    explain: bool,
    deterministic: bool,
    min_confidence: float,
    max_files_rotated: int,
    max_lines_removed: int,
    max_archive_chars: int,
    summary: Summary,
) -> int:
    init_files(root, force=force, summary=summary)
    return run_maintain(
        root=root,
        line_threshold=line_threshold,
        keep_last=keep_last,
        task_days=task_days,
        plan_file=None,
        dry_run=dry_run,
        explain=explain,
        deterministic=deterministic,
        min_confidence=min_confidence,
        max_files_rotated=max_files_rotated,
        max_lines_removed=max_lines_removed,
        max_archive_chars=max_archive_chars,
        no_fallback=False,
        summary=summary,
    )


def add_common_maintain_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--line-threshold", type=int, default=100, help="Rotate file if line count exceeds this.")
    parser.add_argument("--keep-last", type=int, default=60, help="After rotation, keep this many lines.")
    parser.add_argument("--task-days", type=int, default=30, help="Archive completed tasks older than this.")
    parser.add_argument("--plan-file", help="Optional JSON plan generated by an LLM.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    parser.add_argument("--explain", action="store_true", help="Print reasons and thresholds for each action.")
    parser.add_argument(
        "--deterministic",
        action="store_true",
        help="Sort operations by file name for stable execution ordering.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Skip plan rules with confidence below this threshold (0.0 to 1.0).",
    )
    parser.add_argument(
        "--max-files-rotated",
        type=int,
        default=5,
        help="Safety cap: maximum number of files rotated per run.",
    )
    parser.add_argument(
        "--max-lines-removed",
        type=int,
        default=1200,
        help="Safety cap: maximum total lines removed in one run.",
    )
    parser.add_argument(
        "--max-archive-chars",
        type=int,
        default=250000,
        help="Safety cap: maximum archive character growth in one run.",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="When plan validation fails, do not fallback to deterministic defaults.",
    )


def add_plan_check_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--plan-file", required=True, help="JSON plan file to validate.")
    parser.add_argument(
        "--deterministic",
        action="store_true",
        help="Sort operations by file name for stable analysis ordering.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Skip plan rules with confidence below this threshold (0.0 to 1.0).",
    )
    parser.add_argument("--max-files-rotated", type=int, default=5)
    parser.add_argument("--max-lines-removed", type=int, default=1200)
    parser.add_argument("--max-archive-chars", type=int, default=250000)


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
    add_common_maintain_options(p_maintain)

    p_all = sub.add_parser("all", help="Run init and maintain in one command.")
    p_all.add_argument("--force", action="store_true", help="Overwrite existing core files in init step.")
    add_common_maintain_options(p_all)

    sub.add_parser("status", help="Show missing core files and simple line counts.")
    p_check = sub.add_parser("plan-check", help="Validate a plan and simulate actions without writing files.")
    add_plan_check_options(p_check)
    p_plan_init = sub.add_parser(
        "plan-init",
        help="Create a ready-to-use .ai/maintain-plan.json from template + defaults.",
    )
    p_plan_init.add_argument(
        "--output",
        default=".ai/maintain-plan.json",
        help="Output plan path (default: .ai/maintain-plan.json).",
    )
    p_plan_init.add_argument("--force", action="store_true", help="Overwrite existing output plan file.")
    sub.add_parser("plan-schema", help="Write and print the JSON schema for maintain plans.")
    sub.add_parser("llm-prompt", help="Print a complete prompt block for generating a maintain plan.")

    p_skill = sub.add_parser(
        "skill",
        help="Single entrypoint for skill wrappers.",
    )
    p_skill.add_argument(
        "action",
        choices=[
            "status",
            "init",
            "maintain",
            "all",
            "llm-plan-input",
            "plan-template",
            "plan-schema",
            "plan-check",
            "plan-init",
            "llm-prompt",
        ],
        help="Action to run.",
    )
    p_skill.add_argument("--force", action="store_true", help="Overwrite existing core files for init/all.")
    p_skill.add_argument("--output", default=".ai/maintain-plan.json", help="Output plan path for plan-init action.")
    add_common_maintain_options(p_skill)

    sub.add_parser(
        "llm-plan-input",
        help="Print JSON context that an LLM can use to create a maintain plan.",
    )
    sub.add_parser(
        "plan-template",
        help="Print a valid JSON template for maintain --plan-file.",
    )

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
        return run_init(root, force=args.force, summary=summary)
    if args.command == "maintain":
        return run_maintain(
            root,
            line_threshold=args.line_threshold,
            keep_last=args.keep_last,
            task_days=args.task_days,
            plan_file=args.plan_file,
            dry_run=args.dry_run,
            explain=args.explain,
            deterministic=args.deterministic,
            min_confidence=args.min_confidence,
            max_files_rotated=args.max_files_rotated,
            max_lines_removed=args.max_lines_removed,
            max_archive_chars=args.max_archive_chars,
            no_fallback=args.no_fallback,
            summary=summary,
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
            deterministic=args.deterministic,
            min_confidence=args.min_confidence,
            max_files_rotated=args.max_files_rotated,
            max_lines_removed=args.max_lines_removed,
            max_archive_chars=args.max_archive_chars,
            summary=summary,
        )
    if args.command == "status":
        return status(root)
    if args.command == "plan-check":
        return run_plan_check(
            root=root,
            plan_file=args.plan_file,
            min_confidence=args.min_confidence,
            deterministic=args.deterministic,
            max_files_rotated=args.max_files_rotated,
            max_lines_removed=args.max_lines_removed,
            max_archive_chars=args.max_archive_chars,
        )
    if args.command == "plan-init":
        return run_plan_init(
            root=root,
            output=args.output,
            force=args.force,
            summary=summary,
        )
    if args.command == "plan-schema":
        return run_plan_schema(root, summary)
    if args.command == "llm-prompt":
        return run_llm_prompt(root)
    if args.command == "llm-plan-input":
        return run_llm_plan_input(root)
    if args.command == "plan-template":
        return run_plan_template()
    if args.command == "skill":
        if args.action == "status":
            return status(root)
        if args.action == "init":
            return run_init(root, force=args.force, summary=summary)
        if args.action == "maintain":
            return run_maintain(
                root,
                line_threshold=args.line_threshold,
                keep_last=args.keep_last,
                task_days=args.task_days,
                plan_file=args.plan_file,
                dry_run=args.dry_run,
                explain=args.explain,
                deterministic=args.deterministic,
                min_confidence=args.min_confidence,
                max_files_rotated=args.max_files_rotated,
                max_lines_removed=args.max_lines_removed,
                max_archive_chars=args.max_archive_chars,
                no_fallback=args.no_fallback,
                summary=summary,
            )
        if args.action == "all":
            return run_all(
                root,
                force=args.force,
                line_threshold=args.line_threshold,
                keep_last=args.keep_last,
                task_days=args.task_days,
                dry_run=args.dry_run,
                explain=args.explain,
                deterministic=args.deterministic,
                min_confidence=args.min_confidence,
                max_files_rotated=args.max_files_rotated,
                max_lines_removed=args.max_lines_removed,
                max_archive_chars=args.max_archive_chars,
                summary=summary,
            )
        if args.action == "llm-plan-input":
            return run_llm_plan_input(root)
        if args.action == "plan-template":
            return run_plan_template()
        if args.action == "plan-schema":
            return run_plan_schema(root, summary)
        if args.action == "plan-check":
            if not args.plan_file:
                print("`--plan-file` is required for plan-check.", file=sys.stderr)
                return 2
            return run_plan_check(
                root=root,
                plan_file=args.plan_file,
                min_confidence=args.min_confidence,
                deterministic=args.deterministic,
                max_files_rotated=args.max_files_rotated,
                max_lines_removed=args.max_lines_removed,
                max_archive_chars=args.max_archive_chars,
            )
        if args.action == "plan-init":
            return run_plan_init(
                root=root,
                output=args.output,
                force=args.force,
                summary=summary,
            )
        if args.action == "llm-prompt":
            return run_llm_prompt(root)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
