"""CLI argument parsing and command dispatch."""

from __future__ import annotations

import argparse
from pathlib import Path

from .files import COMPRESSIBLE_FILES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextkit",
        description="Full SDLC memory system for AI coding agents.",
    )
    parser.add_argument("--root", default=".", help="Project root (default: current directory).")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- Init & Status ---
    p_init = sub.add_parser("init", help="Create .ai files and archive structure.")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing core files.")

    sub.add_parser("status", help="Show file sizes and missing files.")

    # --- Maintenance ---
    p_maintain = sub.add_parser("maintain", help="Rotate large files, archive old tasks.")
    p_maintain.add_argument("--line-threshold", type=int, default=100, help="Rotate files with >N lines (default: 100)")
    p_maintain.add_argument("--keep-last", type=int, default=60, help="Keep last N lines when rotating (default: 60)")
    p_maintain.add_argument("--task-days", type=int, default=30, help="Archive tasks older than N days (default: 30)")
    p_maintain.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    p_maintain.add_argument("--explain", action="store_true", help="Show what would be done and why")

    p_all = sub.add_parser("all", help="Run init + maintain.")
    p_all.add_argument("--force", action="store_true")
    p_all.add_argument("--line-threshold", type=int, default=100)
    p_all.add_argument("--keep-last", type=int, default=60)
    p_all.add_argument("--task-days", type=int, default=30)
    p_all.add_argument("--dry-run", action="store_true")
    p_all.add_argument("--explain", action="store_true")

    # --- Compression (LLM-driven) ---
    p_compress = sub.add_parser("compress", help="Compress accumulating .ai files with AI summarization.")
    p_compress.add_argument("--write", type=str, metavar="FILE", help="Write compressed content for a specific file")
    p_compress.add_argument("--content", type=str, help="Compressed content to write (with --write)")
    p_compress.add_argument("--no-archive", action="store_true", help="Don't archive the original")

    # --- Planning (Requirements) ---
    p_req = sub.add_parser("add-requirement", help="Add a feature requirement.")
    p_req.add_argument("req_id", type=str, help="Requirement ID (e.g., REQ-001)")
    p_req.add_argument("title", type=str, help="Requirement title")
    p_req.add_argument("--user-story", required=True, help="As a [user], I want [goal] so that [benefit]")
    p_req.add_argument("--priority", default="Medium", help="High, Medium, Low (default: Medium)")
    p_req.add_argument("--acceptance", default="", help="Acceptance criteria (pipe-separated)")

    p_req_done = sub.add_parser("requirement-done", help="Mark a requirement as done.")
    p_req_done.add_argument("req_id", type=str, help="Requirement ID")
    p_req_done.add_argument("--notes", default="", help="Implementation notes")

    # --- Design ---
    p_design = sub.add_parser("update-design", help="Update DESIGN.md section.")
    p_design.add_argument("section", type=str, help="Section: architecture|backend|frontend|ui-patterns|data-models|api|state|dependencies")
    p_design.add_argument("content", type=str, help="Section content (markdown)")

    # --- Development ---
    p_decision = sub.add_parser("add-decision", help="Record an architecture decision.")
    p_decision.add_argument("title", type=str, help="Decision title")
    p_decision.add_argument("--context", required=True, help="Why this decision was needed")
    p_decision.add_argument("--decision", required=True, help="What was decided")
    p_decision.add_argument("--consequences", required=True, help="Trade-offs and implications")
    p_decision.add_argument("--status", default="Proposed", help="Decision status (default: Proposed)")

    p_pattern = sub.add_parser("add-pattern", help="Record a code pattern.")
    p_pattern.add_argument("category", type=str, help="Pattern category (e.g., 'Structure', 'Naming')")
    p_pattern.add_argument("title", type=str, help="Pattern title")
    p_pattern.add_argument("description", type=str, help="Pattern description")

    p_lesson = sub.add_parser("add-lesson", help="Document a lesson learned.")
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

    p_task = sub.add_parser("task-done", help="Mark a task as completed.")
    p_task.add_argument("task", type=str, help="Task description")

    # --- Testing ---
    p_testing = sub.add_parser("update-testing", help="Update TESTING.md with current status.")
    p_testing.add_argument("--unit", type=str, help="Unit test coverage %%")
    p_testing.add_argument("--integration", type=str, help="Integration test coverage %%")
    p_testing.add_argument("--e2e", type=str, help="E2E test coverage %%")
    p_testing.add_argument("--gaps", type=str, help="Known test gaps (pipe-separated)")
    p_testing.add_argument("--benchmarks", type=str, help="Performance benchmarks (pipe-separated)")

    # --- Release ---
    p_release = sub.add_parser("add-release", help="Add release notes.")
    p_release.add_argument("version", type=str, help="Version (e.g., v0.1.0)")
    p_release.add_argument("--added", type=str, help="New features (pipe-separated)")
    p_release.add_argument("--changed", type=str, help="Changed behavior (pipe-separated)")
    p_release.add_argument("--fixed", type=str, help="Bug fixes (pipe-separated)")
    p_release.add_argument("--deployment", type=str, help="Deployment notes (pipe-separated)")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    ai_dir = root / ".ai"

    # Init & Status
    if args.command == "init":
        from .commands import run_init
        return run_init(root, force=args.force)

    if args.command == "status":
        from .commands import run_status
        return run_status(root)

    # Maintenance
    if args.command == "maintain":
        from .maintain import run_maintain
        return run_maintain(
            root,
            line_threshold=args.line_threshold,
            keep_last=args.keep_last,
            task_days=args.task_days,
            dry_run=args.dry_run,
            explain=args.explain,
        )

    if args.command == "all":
        from .maintain import run_all
        return run_all(
            root,
            force=args.force,
            line_threshold=args.line_threshold,
            keep_last=args.keep_last,
            task_days=args.task_days,
            dry_run=args.dry_run,
            explain=args.explain,
        )

    # Compression
    if args.command == "compress":
        from .compress import run_compress, run_compress_write
        if args.write:
            if not args.content:
                print("ERROR: --content is required with --write")
                return 1
            return run_compress_write(
                ai_dir,
                file_name=args.write,
                content=args.content,
                archive_original=not args.no_archive,
            )
        return run_compress(ai_dir)

    # Planning
    if args.command == "add-requirement":
        from .commands import run_add_requirement
        return run_add_requirement(
            ai_dir,
            req_id=args.req_id,
            title=args.title,
            user_story=args.user_story,
            priority=args.priority,
            acceptance_criteria=args.acceptance or "",
        )

    if args.command == "requirement-done":
        from .commands import run_requirement_done
        return run_requirement_done(
            ai_dir,
            req_id=args.req_id,
            notes=args.notes or "",
        )

    # Design
    if args.command == "update-design":
        from .commands import run_update_design
        return run_update_design(
            ai_dir,
            section=args.section,
            content=args.content,
        )

    # Development
    if args.command == "add-decision":
        from .commands import run_add_decision
        return run_add_decision(
            ai_dir,
            title=args.title,
            context=args.context,
            decision=args.decision,
            consequences=args.consequences,
            status=args.status,
        )

    if args.command == "add-pattern":
        from .commands import run_add_pattern
        return run_add_pattern(
            ai_dir,
            category=args.category,
            title=args.title,
            description=args.description,
        )

    if args.command == "add-lesson":
        from .commands import run_add_lesson
        return run_add_lesson(
            ai_dir,
            title=args.title,
            symptom=args.symptom,
            root_cause=args.root_cause,
            fix=args.fix,
            prevention=args.prevention,
        )

    if args.command == "update-context":
        from .commands import run_update_context
        return run_update_context(
            ai_dir,
            change=args.change or "",
            context=args.context or "",
            blocker=args.blocker or "",
            next_steps=args.next_steps or "",
        )

    if args.command == "task-done":
        from .commands import run_task_done
        return run_task_done(ai_dir, task=args.task)

    # Testing
    if args.command == "update-testing":
        from .commands import run_update_testing
        return run_update_testing(
            ai_dir,
            coverage_unit=args.unit or "",
            coverage_integration=args.integration or "",
            coverage_e2e=args.e2e or "",
            gaps=args.gaps or "",
            benchmarks=args.benchmarks or "",
        )

    # Release
    if args.command == "add-release":
        from .commands import run_add_release
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
    import sys
    sys.exit(main())
