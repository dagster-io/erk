"""Tests for legacy .erk/docs/agent/ health check (dogfooder feature)."""

from pathlib import Path

from erk.core.health_checks_dogfooder.legacy_erk_docs_agent import (
    check_legacy_erk_docs_agent,
)


def test_check_passes_when_no_docs_directory(tmp_path: Path) -> None:
    """Test check passes when .erk/docs/agent/ doesn't exist."""
    result = check_legacy_erk_docs_agent(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert result.name == "legacy erk docs"
    assert "No legacy" in result.message


def test_check_passes_when_erk_dir_has_no_docs(tmp_path: Path) -> None:
    """Test check passes when .erk/ exists but docs/agent/ doesn't."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    (erk_dir / "config.toml").write_text("[config]\n", encoding="utf-8")

    result = check_legacy_erk_docs_agent(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert "No legacy" in result.message


def test_check_passes_when_docs_agent_directory_is_empty(tmp_path: Path) -> None:
    """Test check passes when .erk/docs/agent/ exists but is empty."""
    agent_docs_dir = tmp_path / ".erk" / "docs" / "agent"
    agent_docs_dir.mkdir(parents=True)

    result = check_legacy_erk_docs_agent(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert "empty directory" in result.message


def test_check_warns_when_docs_agent_has_files(tmp_path: Path) -> None:
    """Test check warns when .erk/docs/agent/ contains files."""
    agent_docs_dir = tmp_path / ".erk" / "docs" / "agent"
    agent_docs_dir.mkdir(parents=True)
    (agent_docs_dir / "architecture.md").write_text("# Architecture\n", encoding="utf-8")

    result = check_legacy_erk_docs_agent(tmp_path)

    assert result.passed is True  # Warning only, doesn't fail
    assert result.warning is True
    assert result.name == "legacy erk docs"
    assert "1 file" in result.message
    assert result.details is not None
    assert "docs/learned" in result.details


def test_check_counts_multiple_files(tmp_path: Path) -> None:
    """Test check counts all files in docs/agent/ directory."""
    agent_docs_dir = tmp_path / ".erk" / "docs" / "agent"
    agent_docs_dir.mkdir(parents=True)
    (agent_docs_dir / "file1.md").write_text("# File 1\n", encoding="utf-8")
    (agent_docs_dir / "file2.md").write_text("# File 2\n", encoding="utf-8")
    (agent_docs_dir / "file3.md").write_text("# File 3\n", encoding="utf-8")

    result = check_legacy_erk_docs_agent(tmp_path)

    assert result.passed is True
    assert result.warning is True
    assert "3 file" in result.message


def test_check_counts_nested_files(tmp_path: Path) -> None:
    """Test check counts files in nested subdirectories."""
    agent_docs_dir = tmp_path / ".erk" / "docs" / "agent"
    (agent_docs_dir / "subdir").mkdir(parents=True)
    (agent_docs_dir / "top.md").write_text("# Top\n", encoding="utf-8")
    (agent_docs_dir / "subdir" / "nested.md").write_text("# Nested\n", encoding="utf-8")

    result = check_legacy_erk_docs_agent(tmp_path)

    assert result.passed is True
    assert result.warning is True
    assert "2 file" in result.message
