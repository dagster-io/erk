"""Tests for orphaned artifact detection."""

from pathlib import Path

import pytest

from erk.artifacts.orphans import find_orphaned_artifacts


def test_find_orphaned_artifacts_no_claude_dir(tmp_path: Path) -> None:
    """Test orphan detection when no .claude/ directory exists."""
    result = find_orphaned_artifacts(tmp_path)

    assert result.skipped_reason == "no-claude-dir"
    assert result.orphans == {}


def test_find_orphaned_artifacts_in_erk_repo(tmp_path: Path) -> None:
    """Test orphan detection in erk repo → skipped."""
    # Create pyproject.toml that makes it look like erk repo
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('name = "erk"\nversion = "1.0.0"', encoding="utf-8")

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    result = find_orphaned_artifacts(tmp_path)

    assert result.skipped_reason == "erk-repo"
    assert result.orphans == {}


def test_find_orphaned_artifacts_no_bundled_dir(
    tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
) -> None:
    """Test orphan detection when bundled .claude/ not found."""
    # Create .claude/ directory
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    # Mock bundled dir to non-existent path
    monkeypatch.setattr(
        "erk.artifacts.orphans.get_bundled_claude_dir", lambda: Path("/nonexistent")
    )

    result = find_orphaned_artifacts(tmp_path)

    assert result.skipped_reason == "no-bundled-dir"
    assert result.orphans == {}


def test_find_orphaned_artifacts_no_orphans(
    tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
) -> None:
    """Test orphan detection when no orphaned files exist."""
    # Create a mock bundled directory
    bundled_dir = tmp_path / "bundled" / ".claude"
    bundled_commands = bundled_dir / "commands" / "erk"
    bundled_commands.mkdir(parents=True)
    (bundled_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")

    # Create project directory with same files (no orphans)
    project_dir = tmp_path / "project"
    project_claude = project_dir / ".claude"
    project_commands = project_claude / "commands" / "erk"
    project_commands.mkdir(parents=True)
    (project_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")

    # Monkeypatch get_bundled_claude_dir to return our mock
    monkeypatch.setattr("erk.artifacts.orphans.get_bundled_claude_dir", lambda: bundled_dir)

    result = find_orphaned_artifacts(project_dir)

    assert result.skipped_reason is None
    assert result.orphans == {}


def test_find_orphaned_artifacts_orphaned_command(
    tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
) -> None:
    """Test orphaned command file is detected."""
    # Create a mock bundled directory with one command
    bundled_dir = tmp_path / "bundled" / ".claude"
    bundled_commands = bundled_dir / "commands" / "erk"
    bundled_commands.mkdir(parents=True)
    (bundled_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")

    # Create project directory with an extra orphaned command
    project_dir = tmp_path / "project"
    project_claude = project_dir / ".claude"
    project_commands = project_claude / "commands" / "erk"
    project_commands.mkdir(parents=True)
    (project_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")
    (project_commands / "old-command.md").write_text("# Orphan", encoding="utf-8")

    monkeypatch.setattr("erk.artifacts.orphans.get_bundled_claude_dir", lambda: bundled_dir)

    result = find_orphaned_artifacts(project_dir)

    assert result.skipped_reason is None
    assert "commands/erk" in result.orphans
    assert "old-command.md" in result.orphans["commands/erk"]


def test_find_orphaned_artifacts_orphaned_skill(
    tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
) -> None:
    """Test orphaned skill file is detected."""
    # Create a mock bundled directory with a skill
    bundled_dir = tmp_path / "bundled" / ".claude"
    bundled_skill = bundled_dir / "skills" / "dignified-python"
    bundled_skill.mkdir(parents=True)
    (bundled_skill / "core.md").write_text("# Core", encoding="utf-8")

    # Create project directory with an extra orphaned file in the skill
    project_dir = tmp_path / "project"
    project_claude = project_dir / ".claude"
    project_skill = project_claude / "skills" / "dignified-python"
    project_skill.mkdir(parents=True)
    (project_skill / "core.md").write_text("# Core", encoding="utf-8")
    (project_skill / "deprecated-file.md").write_text("# Orphan", encoding="utf-8")

    monkeypatch.setattr("erk.artifacts.orphans.get_bundled_claude_dir", lambda: bundled_dir)

    result = find_orphaned_artifacts(project_dir)

    assert result.skipped_reason is None
    assert "skills/dignified-python" in result.orphans
    assert "deprecated-file.md" in result.orphans["skills/dignified-python"]


def test_find_orphaned_artifacts_orphaned_agent(
    tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
) -> None:
    """Test orphaned agent file is detected."""
    # Create a mock bundled directory with an agent
    bundled_dir = tmp_path / "bundled" / ".claude"
    bundled_agent = bundled_dir / "agents" / "devrun"
    bundled_agent.mkdir(parents=True)
    (bundled_agent / "agent.md").write_text("# Agent", encoding="utf-8")

    # Create project directory with an extra orphaned file in the agent
    project_dir = tmp_path / "project"
    project_claude = project_dir / ".claude"
    project_agent = project_claude / "agents" / "devrun"
    project_agent.mkdir(parents=True)
    (project_agent / "agent.md").write_text("# Agent", encoding="utf-8")
    (project_agent / "old-file.md").write_text("# Orphan", encoding="utf-8")

    monkeypatch.setattr("erk.artifacts.orphans.get_bundled_claude_dir", lambda: bundled_dir)

    result = find_orphaned_artifacts(project_dir)

    assert result.skipped_reason is None
    assert "agents/devrun" in result.orphans
    assert "old-file.md" in result.orphans["agents/devrun"]


def test_find_orphaned_artifacts_detects_init_py(
    tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
) -> None:
    """Test that __init__.py files are detected as orphans in commands/erk/."""
    # Create a mock bundled directory
    bundled_dir = tmp_path / "bundled" / ".claude"
    bundled_commands = bundled_dir / "commands" / "erk"
    bundled_commands.mkdir(parents=True)
    (bundled_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")

    # Create project directory with __init__.py (should be flagged as orphan)
    project_dir = tmp_path / "project"
    project_claude = project_dir / ".claude"
    project_commands = project_claude / "commands" / "erk"
    project_commands.mkdir(parents=True)
    (project_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")
    (project_commands / "__init__.py").write_text("", encoding="utf-8")

    monkeypatch.setattr("erk.artifacts.orphans.get_bundled_claude_dir", lambda: bundled_dir)

    result = find_orphaned_artifacts(project_dir)

    assert result.skipped_reason is None
    assert "commands/erk" in result.orphans
    assert "__init__.py" in result.orphans["commands/erk"]


def test_find_orphaned_artifacts_user_created_folders_not_checked(
    tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
) -> None:
    """Test that user-created folders (e.g., local/) are not checked."""
    # Create a mock bundled directory with one command
    bundled_dir = tmp_path / "bundled" / ".claude"
    bundled_commands = bundled_dir / "commands" / "erk"
    bundled_commands.mkdir(parents=True)
    (bundled_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")

    # Create project directory with user-created folders
    project_dir = tmp_path / "project"
    project_claude = project_dir / ".claude"
    project_commands = project_claude / "commands" / "erk"
    project_commands.mkdir(parents=True)
    (project_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")

    # User-created folders - these should NOT be flagged as orphans
    local_commands = project_claude / "commands" / "local"
    local_commands.mkdir(parents=True)
    (local_commands / "my-custom-command.md").write_text("# Custom", encoding="utf-8")

    custom_skill = project_claude / "skills" / "my-custom-skill"
    custom_skill.mkdir(parents=True)
    (custom_skill / "SKILL.md").write_text("# Custom", encoding="utf-8")

    monkeypatch.setattr("erk.artifacts.orphans.get_bundled_claude_dir", lambda: bundled_dir)

    result = find_orphaned_artifacts(project_dir)

    # Should have no orphans - user-created folders are not checked
    assert result.skipped_reason is None
    assert result.orphans == {}
