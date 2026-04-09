"""Tests for contextkit file utilities."""

import tempfile
from pathlib import Path

from contextkit.files import (
    read_text,
    write_text,
    compact_markdown,
    _collapse_blank_lines,
    _prune_empty_h3_sections,
)


class TestReadText:
    def test_read_existing_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("hello")
            path = Path(f.name)
        assert read_text(path) == "hello"

    def test_read_nonexistent_file(self):
        assert read_text(Path("/nonexistent/path")) == ""


class TestWriteText:
    def test_write_creates_dirs(self, tmp_path):
        target = tmp_path / "subdir" / "file.txt"
        write_text(target, "content")
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "content"


class TestCompactMarkdown:
    def test_collapse_blank_lines(self):
        lines = ["a", "", "", "", "b"]
        result = _collapse_blank_lines(lines, max_run=1)
        assert result == ["a", "", "b"]

    def test_prune_empty_h3(self):
        text = """## Header

### Empty Section

### Real Section
Some content
"""
        result = _prune_empty_h3_sections(text)
        assert "Empty Section" not in result
        assert "Real Section" in result

    def test_compact_context_md(self):
        text = """## Header


Some text


More text
"""
        result = compact_markdown(text, "CONTEXT.md")
        # Should not have multiple consecutive blank lines
        assert "\n\n\n" not in result

    def test_compact_preserves_content(self):
        text = "### Decision\n- Keep this\n"
        result = compact_markdown(text, "DECISIONS.md")
        assert "Keep this" in result


class TestFileRoundtrip:
    def test_write_and_read(self, tmp_path):
        target = tmp_path / "test.md"
        original = "## Header\n\n### Section\n- item\n"
        write_text(target, original)
        assert read_text(target) == original
