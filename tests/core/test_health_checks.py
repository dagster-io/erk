"""Tests for health_checks module."""

import json
from pathlib import Path
from unittest.mock import patch

from erk_shared.git.fake import FakeGit

from erk.core.health_checks import (
    CheckResult,
    check_claude_settings,
    check_docs_agent,
    check_erk_version,
    check_gitignore_entries,
    check_repository,
    check_uv_version,
)
from tests.fakes.context import create_test_context


def test_check_result_dataclass() -> None:
    """Test CheckResult dataclass creation."""
    result = CheckResult(
        name="test",
        passed=True,
        message="Test passed",
        details="Some details",
    )

    assert result.name == "test"
    assert result.passed is True
    assert result.message == "Test passed"
    assert result.details == "Some details"


def test_check_result_without_details() -> None:
    """Test CheckResult without optional details."""
    result = CheckResult(
        name="test",
        passed=False,
        message="Test failed",
    )

    assert result.name == "test"
    assert result.passed is False
    assert result.message == "Test failed"
    assert result.details is None


def test_check_erk_version() -> None:
    """Test that check_erk_version returns a valid result."""
    result = check_erk_version()

    # Should always pass if erk is installed (which it is since we're running tests)
    assert result.name == "erk"
    assert result.passed is True
    assert "erk" in result.message.lower()


def test_check_claude_settings_no_file(tmp_path: Path) -> None:
    """Test claude settings check when no settings file exists."""
    result = check_claude_settings(tmp_path)

    assert result.name == "claude settings"
    assert result.passed is True
    assert "No .claude/settings.json" in result.message


def test_check_claude_settings_valid_json(tmp_path: Path) -> None:
    """Test claude settings check with valid settings file."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings_file = claude_dir / "settings.json"
    settings_file.write_text(json.dumps({"hooks": {}}), encoding="utf-8")

    result = check_claude_settings(tmp_path)

    assert result.name == "claude settings"
    assert result.passed is True
    assert "looks valid" in result.message.lower() or "using defaults" in result.message.lower()


def test_check_claude_settings_invalid_json(tmp_path: Path) -> None:
    """Test claude settings check with invalid JSON."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings_file = claude_dir / "settings.json"
    settings_file.write_text("{invalid json", encoding="utf-8")

    result = check_claude_settings(tmp_path)

    assert result.name == "claude settings"
    assert result.passed is False
    assert "Invalid JSON" in result.message


def test_check_claude_settings_with_hooks(tmp_path: Path) -> None:
    """Test claude settings check with hook configuration."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings = {
        "hooks": {
            "userPromptSubmit": [
                {
                    "command": "echo hello",
                }
            ]
        }
    }
    settings_file = claude_dir / "settings.json"
    settings_file.write_text(json.dumps(settings), encoding="utf-8")

    result = check_claude_settings(tmp_path)

    assert result.name == "claude settings"
    assert result.passed is True


def test_check_repository_not_in_git_repo(tmp_path: Path) -> None:
    """Test repository check when not in a git repository."""
    # FakeGit with no git_common_dirs configured returns None for get_git_common_dir
    git = FakeGit()
    ctx = create_test_context(git=git, cwd=tmp_path)

    result = check_repository(ctx)

    assert result.name == "repository"
    assert result.passed is False
    assert "Not in a git repository" in result.message


def test_check_repository_in_repo_without_erk(tmp_path: Path) -> None:
    """Test repository check in a git repo without .erk directory."""
    # Configure FakeGit to recognize tmp_path as a git repo
    git = FakeGit(
        git_common_dirs={tmp_path: tmp_path / ".git"},
        repository_roots={tmp_path: tmp_path},
    )
    ctx = create_test_context(git=git, cwd=tmp_path)

    result = check_repository(ctx)

    assert result.name == "repository"
    assert result.passed is True
    assert "no .erk/ directory" in result.message.lower()
    assert result.details is not None
    assert "erk init" in result.details


def test_check_repository_in_repo_with_erk(tmp_path: Path) -> None:
    """Test repository check in a git repo with .erk directory."""
    # Configure FakeGit to recognize tmp_path as a git repo
    git = FakeGit(
        git_common_dirs={tmp_path: tmp_path / ".git"},
        repository_roots={tmp_path: tmp_path},
    )
    ctx = create_test_context(git=git, cwd=tmp_path)

    # Create .erk directory
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()

    result = check_repository(ctx)

    assert result.name == "repository"
    assert result.passed is True
    assert "erk setup detected" in result.message.lower()


def test_check_repository_uses_repo_root_not_cwd(tmp_path: Path) -> None:
    """Test that check_repository looks for .erk at repo root, not cwd."""
    # Create subdirectory structure
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    subdir = repo_root / "src" / "project"
    subdir.mkdir(parents=True)

    # Configure FakeGit so cwd is in a subdirectory but repo root is tmp_path/repo
    git = FakeGit(
        git_common_dirs={subdir: repo_root / ".git"},
        repository_roots={subdir: repo_root},
    )
    ctx = create_test_context(git=git, cwd=subdir)

    # Create .erk at repo root (not in cwd)
    erk_dir = repo_root / ".erk"
    erk_dir.mkdir()

    result = check_repository(ctx)

    # Should find .erk at repo root even though cwd is a subdirectory
    assert result.name == "repository"
    assert result.passed is True
    assert "erk setup detected" in result.message.lower()


# --- Gitignore Tests ---


def test_check_gitignore_entries_no_gitignore(tmp_path: Path) -> None:
    """Test gitignore check when no .gitignore file exists."""
    result = check_gitignore_entries(tmp_path)

    assert result.name == "gitignore"
    assert result.passed is True
    assert "No .gitignore file" in result.message


def test_check_gitignore_entries_all_present(tmp_path: Path) -> None:
    """Test gitignore check when all required entries are present."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n.erk/scratch/\n.impl/\n", encoding="utf-8")

    result = check_gitignore_entries(tmp_path)

    assert result.name == "gitignore"
    assert result.passed is True
    assert "Required gitignore entries present" in result.message


def test_check_gitignore_entries_missing_scratch(tmp_path: Path) -> None:
    """Test gitignore check when .erk/scratch/ entry is missing."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n.impl/\n", encoding="utf-8")

    result = check_gitignore_entries(tmp_path)

    assert result.name == "gitignore"
    assert result.passed is False
    assert ".erk/scratch/" in result.message
    assert result.details is not None
    assert "erk init" in result.details


def test_check_gitignore_entries_missing_impl(tmp_path: Path) -> None:
    """Test gitignore check when .impl/ entry is missing."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n.erk/scratch/\n", encoding="utf-8")

    result = check_gitignore_entries(tmp_path)

    assert result.name == "gitignore"
    assert result.passed is False
    assert ".impl/" in result.message
    assert result.details is not None
    assert "erk init" in result.details


def test_check_gitignore_entries_missing_both(tmp_path: Path) -> None:
    """Test gitignore check when both required entries are missing."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n__pycache__/\n", encoding="utf-8")

    result = check_gitignore_entries(tmp_path)

    assert result.name == "gitignore"
    assert result.passed is False
    assert ".erk/scratch/" in result.message
    assert ".impl/" in result.message
    assert result.details is not None
    assert "erk init" in result.details


# --- UV Version Check Tests ---


def test_check_uv_version_not_found() -> None:
    """Test check_uv_version when uv is not installed."""
    with patch("erk.core.health_checks.shutil.which", return_value=None):
        result = check_uv_version()

    assert result.name == "uv"
    assert result.passed is False
    assert "not found in PATH" in result.message
    assert result.details is not None
    assert "https://docs.astral.sh/uv" in result.details


def test_check_uv_version_available() -> None:
    """Test check_uv_version when uv is installed."""
    with (
        patch("erk.core.health_checks.shutil.which", return_value="/usr/bin/uv"),
        patch("erk.core.health_checks.subprocess.run") as mock_run,
    ):
        mock_run.return_value.stdout = "uv 0.9.2"
        mock_run.return_value.stderr = ""

        result = check_uv_version()

    assert result.name == "uv"
    assert result.passed is True
    assert "0.9.2" in result.message
    assert result.details is not None
    assert "uv self update" in result.details


def test_check_uv_version_with_build_info() -> None:
    """Test check_uv_version parses version with build info."""
    with (
        patch("erk.core.health_checks.shutil.which", return_value="/usr/bin/uv"),
        patch("erk.core.health_checks.subprocess.run") as mock_run,
    ):
        mock_run.return_value.stdout = "uv 0.9.2 (Homebrew 2025-10-10)"
        mock_run.return_value.stderr = ""

        result = check_uv_version()

    assert result.name == "uv"
    assert result.passed is True
    assert "0.9.2" in result.message
    # Should NOT include the build info in version
    assert "Homebrew" not in result.message


# --- docs/agent Tests ---


def test_check_docs_agent_no_directory(tmp_path: Path) -> None:
    """Test docs/agent check when directory doesn't exist."""
    result = check_docs_agent(tmp_path)

    assert result.name == "docs/agent"
    assert result.passed is True
    assert "No docs/agent/ directory" in result.message
    assert result.details is not None
    assert "erk init" in result.details


def test_check_docs_agent_all_templates_present(tmp_path: Path) -> None:
    """Test docs/agent check when all template files exist."""
    docs_agent = tmp_path / "docs" / "agent"
    docs_agent.mkdir(parents=True)

    # Create all expected template files
    (docs_agent / "glossary.md").write_text("# Glossary", encoding="utf-8")
    (docs_agent / "conventions.md").write_text("# Conventions", encoding="utf-8")
    (docs_agent / "guide.md").write_text("# Guide", encoding="utf-8")

    result = check_docs_agent(tmp_path)

    assert result.name == "docs/agent"
    assert result.passed is True
    assert "Agent documentation templates present" in result.message
    assert result.details is None


def test_check_docs_agent_missing_glossary(tmp_path: Path) -> None:
    """Test docs/agent check when glossary.md is missing."""
    docs_agent = tmp_path / "docs" / "agent"
    docs_agent.mkdir(parents=True)

    # Create only some template files
    (docs_agent / "conventions.md").write_text("# Conventions", encoding="utf-8")
    (docs_agent / "guide.md").write_text("# Guide", encoding="utf-8")

    result = check_docs_agent(tmp_path)

    assert result.name == "docs/agent"
    assert result.passed is True  # Info level, not failure
    assert "glossary.md" in result.message
    assert result.details is not None
    assert "erk init --force" in result.details


def test_check_docs_agent_missing_multiple(tmp_path: Path) -> None:
    """Test docs/agent check when multiple template files are missing."""
    docs_agent = tmp_path / "docs" / "agent"
    docs_agent.mkdir(parents=True)

    # Create only guide.md
    (docs_agent / "guide.md").write_text("# Guide", encoding="utf-8")

    result = check_docs_agent(tmp_path)

    assert result.name == "docs/agent"
    assert result.passed is True  # Info level, not failure
    assert "glossary.md" in result.message
    assert "conventions.md" in result.message
    assert result.details is not None
    assert "erk init --force" in result.details


def test_check_docs_agent_empty_directory(tmp_path: Path) -> None:
    """Test docs/agent check when directory exists but is empty."""
    docs_agent = tmp_path / "docs" / "agent"
    docs_agent.mkdir(parents=True)

    result = check_docs_agent(tmp_path)

    assert result.name == "docs/agent"
    assert result.passed is True  # Info level
    # All three files should be mentioned as missing
    assert "glossary.md" in result.message
    assert "conventions.md" in result.message
    assert "guide.md" in result.message
