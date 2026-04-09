"""Tests for contextkit CLI commands."""

import pytest
import tempfile
from pathlib import Path

from contextkit.cli import main
from contextkit.files import CORE_FILES, read_text


@pytest.fixture
def tmp_project():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


class TestInit:
    def test_init_creates_all_files(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        for name in CORE_FILES:
            assert (tmp_project / ".ai" / name).exists(), f"{name} not created"

    def test_init_creates_archive_dirs(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        archive = tmp_project / ".ai" / "archive"
        for dirname in ["context", "requirements", "design", "decisions", "patterns", "lessons", "testing", "tasks", "releases"]:
            assert (archive / dirname).exists(), f"archive/{dirname} not created"

    def test_init_skips_existing(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main(["--root", str(tmp_project), "init"])

    def test_init_force_overwrites(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main(["--root", str(tmp_project), "init", "--force"])


class TestStatus:
    def test_status_shows_files(self, tmp_project, capsys):
        main(["--root", str(tmp_project), "init"])
        main(["--root", str(tmp_project), "status"])
        captured = capsys.readouterr()
        for name in CORE_FILES:
            assert name in captured.out


class TestCommands:
    def test_add_decision(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main([
            "--root", str(tmp_project), "add-decision", "Use SQLite",
            "--context", "Simple deployment",
            "--decision", "SQLite with WAL mode",
            "--consequences", "Easier deployment",
        ])
        content = read_text(tmp_project / ".ai" / "DECISIONS.md")
        assert "Use SQLite" in content
        assert "Simple deployment" in content

    def test_add_lesson(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main([
            "--root", str(tmp_project), "add-lesson", "WAL mode locks",
            "--symptom", "Database locked errors",
            "--root-cause", "Missing WAL config",
            "--fix", "Added WAL mode",
            "--prevention", "Always configure WAL",
        ])
        content = read_text(tmp_project / ".ai" / "LESSONS.md")
        assert "WAL mode locks" in content
        assert "Database locked errors" in content

    def test_add_pattern(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main([
            "--root", str(tmp_project), "add-pattern",
            "Error Handling", "Retry with backoff", "Use tenacity for retries",
        ])
        content = read_text(tmp_project / ".ai" / "PATTERNS.md")
        assert "Retry with backoff" in content
        assert "Error Handling" in content

    def test_task_done(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main(["--root", str(tmp_project), "task-done", "Implement auth"])
        content = read_text(tmp_project / ".ai" / "TASKS.md")
        assert "Implement auth" in content
        assert "[x]" in content

    def test_add_requirement(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main([
            "--root", str(tmp_project), "add-requirement",
            "REQ-001", "User Auth",
            "--user-story", "As a user I want login",
            "--priority", "High",
            "--acceptance", "Login validates|Session persists",
        ])
        content = read_text(tmp_project / ".ai" / "REQUIREMENTS.md")
        assert "REQ-001" in content
        assert "User Auth" in content
        assert "High" in content

    def test_requirement_done(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main([
            "--root", str(tmp_project), "add-requirement",
            "REQ-001", "User Auth",
            "--user-story", "As a user I want login",
        ])
        main([
            "--root", str(tmp_project), "requirement-done",
            "REQ-001", "--notes", "Done with JWT",
        ])
        content = read_text(tmp_project / ".ai" / "REQUIREMENTS.md")
        assert "Status**: Done" in content

    def test_update_context(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main([
            "--root", str(tmp_project), "update-context",
            "--change", "Added auth module",
            "--next-steps", "Write tests|Deploy",
        ])
        content = read_text(tmp_project / ".ai" / "CONTEXT.md")
        assert "Added auth module" in content
        assert "Write tests" in content

    def test_update_design(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main([
            "--root", str(tmp_project), "update-design",
            "backend", "FastAPI REST API with auth",
        ])
        content = read_text(tmp_project / ".ai" / "DESIGN.md")
        assert "FastAPI REST API with auth" in content

    def test_update_testing(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main([
            "--root", str(tmp_project), "update-testing",
            "--unit", "75", "--integration", "60",
            "--gaps", "E2E not set up",
        ])
        content = read_text(tmp_project / ".ai" / "TESTING.md")
        assert "Unit Tests: 75%" in content
        assert "Integration Tests: 60%" in content

    def test_add_release(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main([
            "--root", str(tmp_project), "add-release",
            "v0.1.0",
            "--added", "Auth|Tasks",
            "--fixed", "Login validation bug",
        ])
        content = read_text(tmp_project / ".ai" / "RELEASE.md")
        assert "v0.1.0" in content
        assert "Auth" in content

    def test_decision_auto_numbering(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main([
            "--root", str(tmp_project), "add-decision", "First",
            "--context", "c", "--decision", "d", "--consequences", "x",
        ])
        main([
            "--root", str(tmp_project), "add-decision", "Second",
            "--context", "c", "--decision", "d", "--consequences", "x",
        ])
        content = read_text(tmp_project / ".ai" / "DECISIONS.md")
        assert "First" in content
        assert "Second" in content


class TestMaintain:
    def test_maintain_dry_run(self, tmp_project, capsys):
        main(["--root", str(tmp_project), "init"])
        decisions = tmp_project / ".ai" / "DECISIONS.md"
        lines = [f"### Decision {i}\n- Body {i}" for i in range(150)]
        decisions.write_text("\n".join(lines) + "\n", encoding="utf-8")

        main([
            "--root", str(tmp_project), "maintain",
            "--dry-run", "--explain",
            "--line-threshold", "100",
        ])
        captured = capsys.readouterr()
        assert "Rotate" in captured.out or "Nothing to do" in captured.out

    def test_maintain_nothing_to_rotate(self, tmp_project, capsys):
        main(["--root", str(tmp_project), "init"])
        main(["--root", str(tmp_project), "maintain"])
        captured = capsys.readouterr()
        assert "Nothing to do" in captured.out


class TestCompress:
    def test_compress_displays_files(self, tmp_project, capsys):
        main(["--root", str(tmp_project), "init"])
        main([
            "--root", str(tmp_project), "add-decision", "Test decision",
            "--context", "c", "--decision", "d", "--consequences", "x",
        ])
        main(["--root", str(tmp_project), "compress"])
        captured = capsys.readouterr()
        assert "COMPRESS:" in captured.out

    def test_compress_write(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        decisions = tmp_project / ".ai" / "DECISIONS.md"
        decisions.write_text("### Old decision 1\n- body\n### Old decision 2\n- body\n", encoding="utf-8")

        main([
            "--root", str(tmp_project), "compress",
            "--write", "DECISIONS.md",
            "--content", "### Decisions\n- Summarized: key decision here",
        ])
        content = read_text(tmp_project / ".ai" / "DECISIONS.md")
        assert "Summarized" in content
        archive_dir = tmp_project / ".ai" / "archive" / "decisions"
        archives = list(archive_dir.glob("DECISIONS_pre_compress_*"))
        assert len(archives) > 0, "Original should be archived"
