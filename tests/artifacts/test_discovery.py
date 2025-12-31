"""Tests for artifact discovery."""

from pathlib import Path

from erk.artifacts.discovery import (
    discover_artifacts,
    get_artifact_by_name,
)


def test_discover_artifacts_empty_dir(tmp_path: Path) -> None:
    """Returns empty list when .claude/ doesn't exist."""
    result = discover_artifacts(tmp_path / ".claude")
    assert result == []


def test_discover_artifacts_finds_skills(tmp_path: Path) -> None:
    """Discovers skills from skills/<name>/SKILL.md pattern."""
    claude_dir = tmp_path / ".claude"
    skill_dir = claude_dir / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# My Skill", encoding="utf-8")

    result = discover_artifacts(claude_dir)

    assert len(result) == 1
    assert result[0].name == "my-skill"
    assert result[0].artifact_type == "skill"
    assert result[0].path == skill_file


def test_discover_artifacts_finds_commands(tmp_path: Path) -> None:
    """Discovers commands from commands/<namespace>/<name>.md pattern."""
    claude_dir = tmp_path / ".claude"
    cmd_dir = claude_dir / "commands" / "local"
    cmd_dir.mkdir(parents=True)
    cmd_file = cmd_dir / "my-cmd.md"
    cmd_file.write_text("# My Command", encoding="utf-8")

    result = discover_artifacts(claude_dir)

    assert len(result) == 1
    assert result[0].name == "local:my-cmd"
    assert result[0].artifact_type == "command"
    assert result[0].path == cmd_file


def test_discover_artifacts_finds_agents(tmp_path: Path) -> None:
    """Discovers agents from agents/<name>/<name>.md pattern."""
    claude_dir = tmp_path / ".claude"
    agent_dir = claude_dir / "agents" / "my-agent"
    agent_dir.mkdir(parents=True)
    agent_file = agent_dir / "my-agent.md"
    agent_file.write_text("# My Agent", encoding="utf-8")

    result = discover_artifacts(claude_dir)

    assert len(result) == 1
    assert result[0].name == "my-agent"
    assert result[0].artifact_type == "agent"
    assert result[0].path == agent_file


def test_discover_artifacts_sorted_by_type_and_name(tmp_path: Path) -> None:
    """Results are sorted by type then name."""
    claude_dir = tmp_path / ".claude"

    # Create skill
    skill_dir = claude_dir / "skills" / "z-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Z Skill", encoding="utf-8")

    # Create command
    cmd_dir = claude_dir / "commands" / "local"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "a-cmd.md").write_text("# A Cmd", encoding="utf-8")

    result = discover_artifacts(claude_dir)

    # Commands come before skills alphabetically
    assert len(result) == 2
    assert result[0].artifact_type == "command"
    assert result[1].artifact_type == "skill"


def test_get_artifact_by_name_finds_artifact(tmp_path: Path) -> None:
    """Finds artifact by name."""
    claude_dir = tmp_path / ".claude"
    skill_dir = claude_dir / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

    result = get_artifact_by_name(claude_dir, "test-skill", None)

    assert result is not None
    assert result.name == "test-skill"


def test_get_artifact_by_name_returns_none_if_not_found(tmp_path: Path) -> None:
    """Returns None when artifact not found."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    result = get_artifact_by_name(claude_dir, "nonexistent", None)

    assert result is None


def test_get_artifact_by_name_filters_by_type(tmp_path: Path) -> None:
    """Filters by artifact type when specified."""
    claude_dir = tmp_path / ".claude"

    # Create skill and command with same base name
    skill_dir = claude_dir / "skills" / "same-name"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

    result = get_artifact_by_name(claude_dir, "same-name", "skill")
    assert result is not None
    assert result.artifact_type == "skill"

    result = get_artifact_by_name(claude_dir, "same-name", "command")
    assert result is None
