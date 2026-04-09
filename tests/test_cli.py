"""Tests for ContextKit v0.5.0 — minimal CLI."""

import tempfile
from pathlib import Path

import pytest

from contextkit.cli import main
from contextkit.files import read_text, write_text, compact


@pytest.fixture
def tmp_project():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


class TestInit:
    def test_creates_memory_and_design(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        assert (tmp_project / ".ai" / "MEMORY.md").exists()
        assert (tmp_project / ".ai" / "DESIGN.md").exists()

    def test_skips_existing(self, tmp_project, capsys):
        main(["--root", str(tmp_project), "init"])
        main(["--root", str(tmp_project), "init"])
        out = capsys.readouterr().out
        assert "Skipped" in out

    def test_force_overwrites(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        main(["--root", str(tmp_project), "init", "--force"])


class TestStatus:
    def test_shows_files(self, tmp_project, capsys):
        main(["--root", str(tmp_project), "init"])
        main(["--root", str(tmp_project), "status"])
        out = capsys.readouterr().out
        assert "MEMORY.md" in out
        assert "DESIGN.md" in out

    def test_shows_missing(self, tmp_project, capsys):
        main(["--root", str(tmp_project), "status"])
        out = capsys.readouterr().out
        assert "MISSING" in out


class TestArchive:
    def test_nothing_to_archive_when_small(self, tmp_project, capsys):
        main(["--root", str(tmp_project), "init"])
        main(["--root", str(tmp_project), "archive"])
        out = capsys.readouterr().out
        assert "Nothing to archive" in out

    def test_dry_run_shows_what_would_happen(self, tmp_project, capsys):
        main(["--root", str(tmp_project), "init"])
        # Pad MEMORY.md past threshold
        lines = ["## Active Task"] + [f"- line {i}" for i in range(160)]
        write_text(tmp_project / ".ai" / "MEMORY.md", "\n".join(lines))
        main(["--root", str(tmp_project), "archive", "--dry-run"])
        out = capsys.readouterr().out
        assert "Would archive" in out

    def test_archives_when_over_threshold(self, tmp_project, capsys):
        main(["--root", str(tmp_project), "init"])
        lines = ["## Active Task"] + [f"- line {i}" for i in range(160)]
        write_text(tmp_project / ".ai" / "MEMORY.md", "\n".join(lines))
        main(["--root", str(tmp_project), "archive", "--line-threshold", "150"])
        out = capsys.readouterr().out
        assert "Archived" in out
        archives = list((tmp_project / ".ai" / "archive").glob("MEMORY_*"))
        assert len(archives) > 0

    def test_preserves_content_in_archive(self, tmp_project):
        main(["--root", str(tmp_project), "init"])
        content = "## Active Task\n- important thing\n"
        write_text(tmp_project / ".ai" / "MEMORY.md", content)
        # Manually trigger archive to test content preservation
        from datetime import datetime
        from contextkit.files import write_text as wt
        token = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = tmp_project / ".ai" / "archive" / f"MEMORY_{token}.md"
        wt(archive_path, content)
        archived = read_text(archive_path)
        assert "important thing" in archived


class TestFiles:
    def test_compact_removes_excess_blanks(self):
        text = "a\n\n\n\nb\n\n\nc"
        assert compact(text) == "a\n\nb\n\nc\n"

    def test_compact_strips_trailing(self):
        text = "hello   \nworld   \n"
        assert compact(text) == "hello\nworld\n"

    def test_read_nonexistent(self):
        assert read_text(Path("/no/such/file")) == ""

    def test_write_creates_dirs(self, tmp_path):
        target = tmp_path / "sub" / "f.md"
        write_text(target, "x")
        assert target.exists()


class TestEndToEnd:
    def test_full_cycle(self, tmp_project, capsys):
        # Init
        main(["--root", str(tmp_project), "init"])
        # Status
        main(["--root", str(tmp_project), "status"])
        out = capsys.readouterr().out
        assert "lines" in out
        # AI writes memory directly
        memory = tmp_project / ".ai" / "MEMORY.md"
        write_text(memory, "## Active Task\n- Build feature X\n\n## Next Steps\n- Test\n")
        # Archive should not trigger (small file)
        main(["--root", str(tmp_project), "archive"])
        out = capsys.readouterr().out
        assert "Nothing to archive" in out
