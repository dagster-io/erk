"""Tests for artifact discovery."""

from pathlib import Path

from erk.artifacts.discovery import (
    discover_artifacts,
    get_artifact_by_name,
)


def test_discover_artifacts_empty_dir(tmp_path: Path) -> None:
    """Returns empty list when .claude/ doesn't exist."""
    result = discover_artifacts(tmp_path)
    assert result == []


def test_discover_artifacts_finds_skills(tmp_path: Path) -> None:
    """Discovers skills from skills/<name>/SKILL.md pattern."""
    skill_dir = tmp_path / ".claude" / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# My Skill", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    assert len(result) == 1
    assert result[0].name == "my-skill"
    assert result[0].artifact_type == "skill"
    assert result[0].path == skill_file


def test_discover_artifacts_finds_commands(tmp_path: Path) -> None:
    """Discovers commands from commands/<namespace>/<name>.md pattern."""
    cmd_dir = tmp_path / ".claude" / "commands" / "local"
    cmd_dir.mkdir(parents=True)
    cmd_file = cmd_dir / "my-cmd.md"
    cmd_file.write_text("# My Command", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    assert len(result) == 1
    assert result[0].name == "local:my-cmd"
    assert result[0].artifact_type == "command"
    assert result[0].path == cmd_file


def test_discover_artifacts_finds_agents(tmp_path: Path) -> None:
    """Discovers agents from agents/<name>/<name>.md pattern."""
    agent_dir = tmp_path / ".claude" / "agents" / "my-agent"
    agent_dir.mkdir(parents=True)
    agent_file = agent_dir / "my-agent.md"
    agent_file.write_text("# My Agent", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    assert len(result) == 1
    assert result[0].name == "my-agent"
    assert result[0].artifact_type == "agent"
    assert result[0].path == agent_file


def test_discover_artifacts_sorted_by_type_and_name(tmp_path: Path) -> None:
    """Results are sorted by type then name."""
    # Create skill
    skill_dir = tmp_path / ".claude" / "skills" / "z-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Z Skill", encoding="utf-8")

    # Create command
    cmd_dir = tmp_path / ".claude" / "commands" / "local"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "a-cmd.md").write_text("# A Cmd", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    # Commands come before skills alphabetically
    assert len(result) == 2
    assert result[0].artifact_type == "command"
    assert result[1].artifact_type == "skill"


def test_get_artifact_by_name_finds_artifact(tmp_path: Path) -> None:
    """Finds artifact by name."""
    skill_dir = tmp_path / ".claude" / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

    result = get_artifact_by_name(tmp_path, "test-skill", None)

    assert result is not None
    assert result.name == "test-skill"


def test_get_artifact_by_name_returns_none_if_not_found(tmp_path: Path) -> None:
    """Returns None when artifact not found."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    result = get_artifact_by_name(tmp_path, "nonexistent", None)

    assert result is None


def test_get_artifact_by_name_filters_by_type(tmp_path: Path) -> None:
    """Filters by artifact type when specified."""
    # Create skill and command with same base name
    skill_dir = tmp_path / ".claude" / "skills" / "same-name"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

    result = get_artifact_by_name(tmp_path, "same-name", "skill")
    assert result is not None
    assert result.artifact_type == "skill"

    result = get_artifact_by_name(tmp_path, "same-name", "command")
    assert result is None


def test_discover_top_level_commands(tmp_path: Path) -> None:
    """Top-level commands (no namespace) should be discovered."""
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    cmd_file = commands_dir / "my-command.md"
    cmd_file.write_text("# My Command", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    assert len(result) == 1
    assert result[0].name == "my-command"
    assert result[0].artifact_type == "command"
    assert result[0].path == cmd_file


def test_discover_workflows_finds_all_workflows(tmp_path: Path) -> None:
    """Discovers all workflows from .github/workflows/."""
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)

    # Create an erk-managed workflow
    erk_workflow = workflows_dir / "erk-impl.yml"
    erk_workflow.write_text("name: Erk Impl", encoding="utf-8")

    # Create user workflows (should be discovered too)
    user_ci_workflow = workflows_dir / "user-ci.yml"
    user_ci_workflow.write_text("name: User CI", encoding="utf-8")

    test_workflow = workflows_dir / "test.yml"
    test_workflow.write_text("name: Test", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    # All workflows should be discovered
    assert len(result) == 3
    workflow_names = {w.name for w in result}
    assert workflow_names == {"erk-impl", "user-ci", "test"}
    assert all(w.artifact_type == "workflow" for w in result)


def test_discover_workflows_without_claude_dir(tmp_path: Path) -> None:
    """Discovers workflows even when .claude/ doesn't exist."""
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)

    # Create erk-managed workflow
    erk_workflow = workflows_dir / "erk-impl.yml"
    erk_workflow.write_text("name: Erk Impl", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    assert len(result) == 1
    assert result[0].artifact_type == "workflow"


def test_discover_workflows_discovers_user_workflows(tmp_path: Path) -> None:
    """Discovers user workflows from .github/workflows/ directory."""
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)

    # Create only user workflows
    (workflows_dir / "ci.yml").write_text("name: CI", encoding="utf-8")
    (workflows_dir / "deploy.yml").write_text("name: Deploy", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    assert len(result) == 2
    workflow_names = {w.name for w in result}
    assert workflow_names == {"ci", "deploy"}
    assert all(w.artifact_type == "workflow" for w in result)


def test_discover_workflows_handles_yaml_extension(tmp_path: Path) -> None:
    """Discovers workflows with .yaml extension in addition to .yml."""
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)

    # Create workflow with .yaml extension
    yaml_workflow = workflows_dir / "deploy.yaml"
    yaml_workflow.write_text("name: Deploy", encoding="utf-8")

    # Create workflow with .yml extension
    yml_workflow = workflows_dir / "test.yml"
    yml_workflow.write_text("name: Test", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    assert len(result) == 2
    workflow_names = {w.name for w in result}
    assert workflow_names == {"deploy", "test"}
    assert all(w.artifact_type == "workflow" for w in result)


def test_discover_workflows_ignores_non_workflow_files(tmp_path: Path) -> None:
    """Ignores non-workflow files in .github/workflows/ directory."""
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)

    # Create valid workflow
    (workflows_dir / "valid.yml").write_text("name: Valid", encoding="utf-8")

    # Create files that should be ignored
    (workflows_dir / "README.md").write_text("# README", encoding="utf-8")
    (workflows_dir / "config.txt").write_text("config", encoding="utf-8")
    (workflows_dir / "script.sh").write_text("#!/bin/bash", encoding="utf-8")

    # Create subdirectory (should be ignored)
    subdir = workflows_dir / "scripts"
    subdir.mkdir()
    (subdir / "helper.yml").write_text("helper", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    # Only valid.yml should be discovered
    assert len(result) == 1
    assert result[0].name == "valid"
    assert result[0].artifact_type == "workflow"


def test_discover_workflows_handles_empty_directory(tmp_path: Path) -> None:
    """Returns empty list when .github/workflows/ exists but is empty."""
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)

    result = discover_artifacts(tmp_path)

    assert len(result) == 0


def test_is_erk_managed_workflow_badge_logic(tmp_path: Path) -> None:
    """Verifies badge logic correctly identifies erk-managed workflows."""
    from erk.cli.commands.artifact.list_cmd import _is_erk_managed

    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)

    # Create erk-managed workflow
    erk_workflow = workflows_dir / "erk-impl.yml"
    erk_workflow.write_text("name: Erk Impl", encoding="utf-8")

    # Create user workflow
    user_workflow = workflows_dir / "user-ci.yml"
    user_workflow.write_text("name: User CI", encoding="utf-8")

    artifacts = discover_artifacts(tmp_path)

    # Find erk-managed workflow
    erk_artifact = next(a for a in artifacts if a.name == "erk-impl")
    assert _is_erk_managed(erk_artifact) is True

    # Find user workflow
    user_artifact = next(a for a in artifacts if a.name == "user-ci")
    assert _is_erk_managed(user_artifact) is False
