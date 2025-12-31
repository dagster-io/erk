"""Tests for legacy .claude/docs/ health check (dogfooder feature)."""

from pathlib import Path

from erk.core.health_checks_dogfooder.legacy_claude_docs import check_legacy_claude_docs


def test_check_passes_when_no_docs_directory(tmp_path: Path) -> None:
    """Test check passes when .claude/docs/ doesn't exist."""
    result = check_legacy_claude_docs(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert result.name == "legacy claude docs"
    assert "No legacy" in result.message


def test_check_passes_when_claude_dir_exists_but_no_docs(tmp_path: Path) -> None:
    """Test check passes when .claude/ exists but docs/ doesn't."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text("{}", encoding="utf-8")

    result = check_legacy_claude_docs(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert "No legacy" in result.message


def test_check_passes_when_docs_directory_is_empty(tmp_path: Path) -> None:
    """Test check passes when .claude/docs/ exists but is empty."""
    docs_dir = tmp_path / ".claude" / "docs"
    docs_dir.mkdir(parents=True)

    result = check_legacy_claude_docs(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert "empty directory" in result.message


def test_check_warns_when_docs_directory_has_markdown_files(tmp_path: Path) -> None:
    """Test check warns when .claude/docs/ contains markdown files."""
    docs_dir = tmp_path / ".claude" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "my-doc.md").write_text("# My Doc\n", encoding="utf-8")

    result = check_legacy_claude_docs(tmp_path)

    assert result.passed is True  # Warning only, doesn't fail
    assert result.warning is True
    assert result.name == "legacy claude docs"
    assert "1 doc" in result.message
    assert result.details is not None
    assert "no longer supported" in result.details
    assert "my-doc.md" in result.details
    assert "skills" in result.details.lower()


def test_check_counts_multiple_markdown_files(tmp_path: Path) -> None:
    """Test check counts all markdown files in docs directory."""
    docs_dir = tmp_path / ".claude" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "doc1.md").write_text("# Doc 1\n", encoding="utf-8")
    (docs_dir / "doc2.md").write_text("# Doc 2\n", encoding="utf-8")
    (docs_dir / "doc3.md").write_text("# Doc 3\n", encoding="utf-8")

    result = check_legacy_claude_docs(tmp_path)

    assert result.passed is True
    assert result.warning is True
    assert "3 doc" in result.message


def test_check_ignores_non_markdown_files(tmp_path: Path) -> None:
    """Test check only considers markdown files."""
    docs_dir = tmp_path / ".claude" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "notes.txt").write_text("Some notes\n", encoding="utf-8")
    (docs_dir / "data.json").write_text("{}\n", encoding="utf-8")

    result = check_legacy_claude_docs(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert "empty directory" in result.message
