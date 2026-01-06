"""Tests for artifact discovery."""

import json
from pathlib import Path

from erk.artifacts.artifact_health import is_erk_managed
from erk.artifacts.discovery import (
    discover_artifacts,
    get_artifact_by_name,
)
from erk.core.claude_settings import (
    ERK_EXIT_PLAN_HOOK_COMMAND,
    ERK_USER_PROMPT_HOOK_COMMAND,
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


def test_discover_artifacts_finds_directory_agents(tmp_path: Path) -> None:
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


def test_discover_artifacts_finds_single_file_agents(tmp_path: Path) -> None:
    """Discovers agents from agents/<name>.md pattern (single-file agents)."""
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    agent_file = agents_dir / "devrun.md"
    agent_file.write_text("# Devrun Agent", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    assert len(result) == 1
    assert result[0].name == "devrun"
    assert result[0].artifact_type == "agent"
    assert result[0].path == agent_file


def test_discover_artifacts_directory_agent_takes_precedence(tmp_path: Path) -> None:
    """Directory-based agent takes precedence over single-file with same name."""
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)

    # Create both single-file and directory-based agent with same name
    single_file = agents_dir / "devrun.md"
    single_file.write_text("# Single-file devrun", encoding="utf-8")

    dir_agent = agents_dir / "devrun"
    dir_agent.mkdir()
    dir_agent_file = dir_agent / "devrun.md"
    dir_agent_file.write_text("# Directory-based devrun", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    # Should only find one agent (directory-based takes precedence)
    assert len(result) == 1
    assert result[0].name == "devrun"
    assert result[0].path == dir_agent_file  # Directory entry point, not single-file


def test_discover_artifacts_finds_mixed_agents(tmp_path: Path) -> None:
    """Discovers both directory-based and single-file agents."""
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)

    # Single-file agent
    (agents_dir / "simple-agent.md").write_text("# Simple", encoding="utf-8")

    # Directory-based agent
    complex_dir = agents_dir / "complex-agent"
    complex_dir.mkdir()
    (complex_dir / "complex-agent.md").write_text("# Complex", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    agent_names = {a.name for a in result}
    assert agent_names == {"simple-agent", "complex-agent"}
    assert all(a.artifact_type == "agent" for a in result)


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


def test_discover_nested_namespaced_commands(tmp_path: Path) -> None:
    """Discovers commands with nested namespaces (e.g., erk:system:impl-execute)."""
    cmd_dir = tmp_path / ".claude" / "commands" / "erk" / "system"
    cmd_dir.mkdir(parents=True)
    cmd_file = cmd_dir / "impl-execute.md"
    cmd_file.write_text("# Command", encoding="utf-8")

    result = discover_artifacts(tmp_path)

    assert len(result) == 1
    assert result[0].name == "erk:system:impl-execute"
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
    assert is_erk_managed(erk_artifact) is True

    # Find user workflow
    user_artifact = next(a for a in artifacts if a.name == "user-ci")
    assert is_erk_managed(user_artifact) is False


def test_discover_hooks_from_settings_json(tmp_path: Path) -> None:
    """Discovers hooks configured in .claude/settings.json."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": ERK_USER_PROMPT_HOOK_COMMAND}],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "ExitPlanMode",
                    "hooks": [{"type": "command", "command": ERK_EXIT_PLAN_HOOK_COMMAND}],
                }
            ],
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    result = discover_artifacts(tmp_path)

    hook_artifacts = [a for a in result if a.artifact_type == "hook"]
    assert len(hook_artifacts) == 2

    hook_names = {a.name for a in hook_artifacts}
    assert hook_names == {"user-prompt-hook", "exit-plan-mode-hook"}


def test_discover_hooks_no_settings_json(tmp_path: Path) -> None:
    """Returns empty list when settings.json doesn't exist."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    result = discover_artifacts(tmp_path)

    hook_artifacts = [a for a in result if a.artifact_type == "hook"]
    assert hook_artifacts == []


def test_discover_hooks_partial_configuration(tmp_path: Path) -> None:
    """Discovers only configured hooks."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    # Only configure user-prompt-hook (not exit-plan-mode-hook)
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": ERK_USER_PROMPT_HOOK_COMMAND}],
                }
            ],
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    result = discover_artifacts(tmp_path)

    hook_artifacts = [a for a in result if a.artifact_type == "hook"]
    assert len(hook_artifacts) == 1
    assert hook_artifacts[0].name == "user-prompt-hook"


def test_is_erk_managed_hook_badge_logic(tmp_path: Path) -> None:
    """Verifies badge logic correctly identifies erk-managed hooks."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": ERK_USER_PROMPT_HOOK_COMMAND}],
                }
            ],
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    artifacts = discover_artifacts(tmp_path)
    hook_artifact = next(a for a in artifacts if a.artifact_type == "hook")

    # user-prompt-hook is in BUNDLED_HOOKS
    assert is_erk_managed(hook_artifact) is True


def test_discover_hooks_finds_local_hooks(tmp_path: Path) -> None:
    """Discovers local/user-defined hooks from settings.json."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": ".claude/hooks/my-custom-hook.sh"}],
                }
            ],
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    result = discover_artifacts(tmp_path)

    hook_artifacts = [a for a in result if a.artifact_type == "hook"]
    assert len(hook_artifacts) == 1
    assert hook_artifacts[0].name == ".claude/hooks/my-custom-hook.sh"


def test_discover_hooks_mixed_erk_and_local(tmp_path: Path) -> None:
    """Discovers both erk-managed and local hooks."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": ERK_USER_PROMPT_HOOK_COMMAND},
                        {"type": "command", "command": ".claude/hooks/my-local-hook.sh"},
                    ],
                }
            ],
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    result = discover_artifacts(tmp_path)

    hook_artifacts = [a for a in result if a.artifact_type == "hook"]
    assert len(hook_artifacts) == 2

    hook_names = {a.name for a in hook_artifacts}
    assert hook_names == {"user-prompt-hook", ".claude/hooks/my-local-hook.sh"}


def test_is_erk_managed_local_hook_badge_logic(tmp_path: Path) -> None:
    """Verifies badge logic correctly identifies local hooks as NOT erk-managed."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": ".claude/hooks/my-local-hook.sh"}],
                }
            ],
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    artifacts = discover_artifacts(tmp_path)
    hook_artifact = next(a for a in artifacts if a.artifact_type == "hook")

    # my-local-hook is NOT in BUNDLED_HOOKS
    assert is_erk_managed(hook_artifact) is False
