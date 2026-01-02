"""Tests for artifact sync."""

from pathlib import Path
from unittest.mock import patch

from erk.artifacts.artifact_health import BUNDLED_AGENTS, BUNDLED_SKILLS
from erk.artifacts.sync import (
    _get_erk_package_dir,
    _is_editable_install,
    _sync_actions,
    _sync_commands,
    _sync_directory_artifacts,
    _sync_feature_workflows,
    _sync_hooks,
    get_bundled_claude_dir,
    get_bundled_github_dir,
    sync_artifacts,
    sync_feature,
)


def test_sync_artifacts_skips_in_erk_repo(tmp_path: Path) -> None:
    """Skips file copying in erk repo but still updates state."""
    # Create pyproject.toml with erk name
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "erk"\n', encoding="utf-8")

    result = sync_artifacts(tmp_path, force=False)

    assert result.success is True
    assert result.artifacts_installed == 0
    assert "Development mode" in result.message


def test_sync_artifacts_fails_when_bundled_not_found(tmp_path: Path) -> None:
    """Fails when bundled .claude/ directory doesn't exist."""
    nonexistent = tmp_path / "nonexistent"
    with patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=nonexistent):
        result = sync_artifacts(tmp_path, force=False)

    assert result.success is False
    assert result.artifacts_installed == 0
    assert "not found" in result.message


def test_sync_artifacts_copies_files(tmp_path: Path) -> None:
    """Copies artifact files from bundled to target."""
    # Create bundled artifacts directory
    bundled_dir = tmp_path / "bundled"
    # Use a skill that's in BUNDLED_SKILLS (dignified-python)
    skill_dir = bundled_dir / "skills" / "dignified-python"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

    # Create target directory (different from bundled)
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    # Mock both bundled dirs - github dir doesn't exist so no workflows synced
    nonexistent = tmp_path / "nonexistent"
    with (
        patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_dir),
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=nonexistent),
        patch("erk.artifacts.sync.get_current_version", return_value="1.0.0"),
    ):
        result = sync_artifacts(target_dir, force=False)

    assert result.success is True
    # 1 skill file + 2 hooks = 3 artifacts
    assert result.artifacts_installed == 3

    # Verify file was copied
    copied_file = target_dir / ".claude" / "skills" / "dignified-python" / "SKILL.md"
    assert copied_file.exists()
    assert copied_file.read_text(encoding="utf-8") == "# Test Skill"


def test_sync_artifacts_saves_state(tmp_path: Path) -> None:
    """Saves state with current version after sync."""
    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    target_dir = tmp_path / "project"
    target_dir.mkdir()

    nonexistent = tmp_path / "nonexistent"
    with (
        patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_dir),
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=nonexistent),
        patch("erk.artifacts.sync.get_current_version", return_value="2.0.0"),
    ):
        sync_artifacts(target_dir, force=False)

    # Verify state was saved
    state_file = target_dir / ".erk" / "state.toml"
    assert state_file.exists()
    content = state_file.read_text(encoding="utf-8")
    assert 'version = "2.0.0"' in content


def test_is_editable_install_returns_true_for_src_layout() -> None:
    """Returns True when erk package is not in site-packages."""
    _get_erk_package_dir.cache_clear()
    with patch(
        "erk.artifacts.sync._get_erk_package_dir",
        return_value=Path("/home/user/code/erk/src/erk"),
    ):
        assert _is_editable_install() is True
    _get_erk_package_dir.cache_clear()


def test_is_editable_install_returns_false_for_site_packages() -> None:
    """Returns False when erk package is in site-packages."""
    _get_erk_package_dir.cache_clear()
    with patch(
        "erk.artifacts.sync._get_erk_package_dir",
        return_value=Path("/home/user/.venv/lib/python3.11/site-packages/erk"),
    ):
        assert _is_editable_install() is False
    _get_erk_package_dir.cache_clear()


def test_get_bundled_claude_dir_editable_install() -> None:
    """Returns .claude/ at repo root for editable installs."""
    _get_erk_package_dir.cache_clear()
    get_bundled_claude_dir.cache_clear()
    with patch(
        "erk.artifacts.sync._get_erk_package_dir",
        return_value=Path("/home/user/code/erk/src/erk"),
    ):
        result = get_bundled_claude_dir()
        assert result == Path("/home/user/code/erk/.claude")
    _get_erk_package_dir.cache_clear()
    get_bundled_claude_dir.cache_clear()


def test_get_bundled_claude_dir_wheel_install() -> None:
    """Returns erk/data/claude/ for wheel installs."""
    _get_erk_package_dir.cache_clear()
    get_bundled_claude_dir.cache_clear()
    with patch(
        "erk.artifacts.sync._get_erk_package_dir",
        return_value=Path("/home/user/.venv/lib/python3.11/site-packages/erk"),
    ):
        result = get_bundled_claude_dir()
        assert result == Path("/home/user/.venv/lib/python3.11/site-packages/erk/data/claude")
    _get_erk_package_dir.cache_clear()
    get_bundled_claude_dir.cache_clear()


def test_get_bundled_github_dir_editable_install() -> None:
    """Returns .github/ at repo root for editable installs."""
    _get_erk_package_dir.cache_clear()
    get_bundled_github_dir.cache_clear()
    with patch(
        "erk.artifacts.sync._get_erk_package_dir",
        return_value=Path("/home/user/code/erk/src/erk"),
    ):
        result = get_bundled_github_dir()
        assert result == Path("/home/user/code/erk/.github")
    _get_erk_package_dir.cache_clear()
    get_bundled_github_dir.cache_clear()


def test_get_bundled_github_dir_wheel_install() -> None:
    """Returns erk/data/github/ for wheel installs."""
    _get_erk_package_dir.cache_clear()
    get_bundled_github_dir.cache_clear()
    with patch(
        "erk.artifacts.sync._get_erk_package_dir",
        return_value=Path("/home/user/.venv/lib/python3.11/site-packages/erk"),
    ):
        result = get_bundled_github_dir()
        assert result == Path("/home/user/.venv/lib/python3.11/site-packages/erk/data/github")
    _get_erk_package_dir.cache_clear()
    get_bundled_github_dir.cache_clear()


def test_sync_artifacts_copies_workflows(tmp_path: Path) -> None:
    """Syncs erk-managed workflow files from bundled to target."""
    # Create bundled .claude/ directory
    bundled_claude = tmp_path / "bundled"
    bundled_claude.mkdir()

    # Create bundled .github/ with workflows
    bundled_github = tmp_path / "bundled_github"
    bundled_workflows = bundled_github / "workflows"
    bundled_workflows.mkdir(parents=True)
    (bundled_workflows / "erk-impl.yml").write_text("name: Erk Impl", encoding="utf-8")
    (bundled_workflows / "other-workflow.yml").write_text("name: Other", encoding="utf-8")

    # Create target directory
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    with (
        patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_claude),
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=bundled_github),
        patch("erk.artifacts.sync.get_current_version", return_value="1.0.0"),
    ):
        result = sync_artifacts(target_dir, force=False)

    assert result.success is True
    # erk-impl.yml + 2 hooks = 3 artifacts
    assert result.artifacts_installed == 3

    # Verify erk-impl.yml was copied
    copied_workflow = target_dir / ".github" / "workflows" / "erk-impl.yml"
    assert copied_workflow.exists()
    assert copied_workflow.read_text(encoding="utf-8") == "name: Erk Impl"

    # Verify other-workflow.yml was NOT copied (not in BUNDLED_WORKFLOWS)
    other_workflow = target_dir / ".github" / "workflows" / "other-workflow.yml"
    assert not other_workflow.exists()


def test_sync_directory_artifacts_only_syncs_bundled_skills(tmp_path: Path) -> None:
    """_sync_directory_artifacts only copies items in the provided name set."""
    source_dir = tmp_path / "source" / "skills"

    # Create a bundled skill (dignified-python is in BUNDLED_SKILLS)
    bundled_skill = source_dir / "dignified-python"
    bundled_skill.mkdir(parents=True)
    (bundled_skill / "SKILL.md").write_text("# Bundled Skill", encoding="utf-8")

    # Create a non-bundled skill (should NOT be synced)
    non_bundled_skill = source_dir / "fake-driven-testing"
    non_bundled_skill.mkdir(parents=True)
    (non_bundled_skill / "SKILL.md").write_text("# Non-bundled Skill", encoding="utf-8")

    target_dir = tmp_path / "target" / "skills"

    copied, _ = _sync_directory_artifacts(source_dir, target_dir, BUNDLED_SKILLS, "skills")

    # Should copy exactly 1 file (the bundled skill)
    assert copied == 1

    # Bundled skill should exist
    assert (target_dir / "dignified-python" / "SKILL.md").exists()

    # Non-bundled skill should NOT exist
    assert not (target_dir / "fake-driven-testing").exists()


def test_sync_directory_artifacts_only_syncs_bundled_agents(tmp_path: Path) -> None:
    """_sync_directory_artifacts only copies items in the provided name set."""
    source_dir = tmp_path / "source" / "agents"

    # Create a bundled agent (devrun is in BUNDLED_AGENTS)
    bundled_agent = source_dir / "devrun"
    bundled_agent.mkdir(parents=True)
    (bundled_agent / "AGENT.md").write_text("# Bundled Agent", encoding="utf-8")

    # Create a non-bundled agent (should NOT be synced)
    non_bundled_agent = source_dir / "haiku-devrun"
    non_bundled_agent.mkdir(parents=True)
    (non_bundled_agent / "AGENT.md").write_text("# Non-bundled Agent", encoding="utf-8")

    target_dir = tmp_path / "target" / "agents"

    copied, _ = _sync_directory_artifacts(source_dir, target_dir, BUNDLED_AGENTS, "agents")

    # Should copy exactly 1 file (the bundled agent)
    assert copied == 1

    # Bundled agent should exist
    assert (target_dir / "devrun" / "AGENT.md").exists()

    # Non-bundled agent should NOT exist
    assert not (target_dir / "haiku-devrun").exists()


def test_sync_commands_only_syncs_erk_namespace(tmp_path: Path) -> None:
    """_sync_commands only copies commands in erk namespace."""
    source_dir = tmp_path / "source" / "commands"

    # Create erk namespace commands
    erk_commands = source_dir / "erk"
    erk_commands.mkdir(parents=True)
    (erk_commands / "plan-implement.md").write_text("# Erk Command", encoding="utf-8")

    # Create local namespace commands (should NOT be synced)
    local_commands = source_dir / "local"
    local_commands.mkdir(parents=True)
    (local_commands / "fast-ci.md").write_text("# Local Command", encoding="utf-8")

    # Create gt namespace commands (should NOT be synced)
    gt_commands = source_dir / "gt"
    gt_commands.mkdir(parents=True)
    (gt_commands / "some-command.md").write_text("# GT Command", encoding="utf-8")

    target_dir = tmp_path / "target" / "commands"

    copied, _ = _sync_commands(source_dir, target_dir)

    # Should copy exactly 1 file (the erk namespace command)
    assert copied == 1

    # Erk command should exist
    assert (target_dir / "erk" / "plan-implement.md").exists()

    # Local and gt commands should NOT exist
    assert not (target_dir / "local").exists()
    assert not (target_dir / "gt").exists()


def test_sync_artifacts_filters_all_artifact_types(tmp_path: Path) -> None:
    """Full integration test: sync_artifacts filters skills, agents, and commands."""
    bundled_claude = tmp_path / "bundled"

    # Create bundled skills (only bundled ones)
    bundled_skill = bundled_claude / "skills" / "dignified-python"
    bundled_skill.mkdir(parents=True)
    (bundled_skill / "SKILL.md").write_text("# Bundled", encoding="utf-8")

    # Create non-bundled skill (simulating editable install with dev artifacts)
    non_bundled_skill = bundled_claude / "skills" / "fake-driven-testing"
    non_bundled_skill.mkdir(parents=True)
    (non_bundled_skill / "SKILL.md").write_text("# Dev Only", encoding="utf-8")

    # Create bundled agent
    bundled_agent = bundled_claude / "agents" / "devrun"
    bundled_agent.mkdir(parents=True)
    (bundled_agent / "AGENT.md").write_text("# Bundled Agent", encoding="utf-8")

    # Create non-bundled agent
    non_bundled_agent = bundled_claude / "agents" / "haiku-devrun"
    non_bundled_agent.mkdir(parents=True)
    (non_bundled_agent / "AGENT.md").write_text("# Dev Only", encoding="utf-8")

    # Create erk commands
    erk_commands = bundled_claude / "commands" / "erk"
    erk_commands.mkdir(parents=True)
    (erk_commands / "plan-implement.md").write_text("# Erk", encoding="utf-8")

    # Create local commands (should not be synced)
    local_commands = bundled_claude / "commands" / "local"
    local_commands.mkdir(parents=True)
    (local_commands / "fast-ci.md").write_text("# Local", encoding="utf-8")

    target_dir = tmp_path / "project"
    target_dir.mkdir()

    nonexistent = tmp_path / "nonexistent"
    with (
        patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_claude),
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=nonexistent),
        patch("erk.artifacts.sync.get_current_version", return_value="1.0.0"),
    ):
        result = sync_artifacts(target_dir, force=False)

    assert result.success is True
    # Should copy: 1 skill + 1 agent + 1 command + 2 hooks = 5 artifacts
    assert result.artifacts_installed == 5

    # Bundled artifacts should exist
    assert (target_dir / ".claude" / "skills" / "dignified-python" / "SKILL.md").exists()
    assert (target_dir / ".claude" / "agents" / "devrun" / "AGENT.md").exists()
    assert (target_dir / ".claude" / "commands" / "erk" / "plan-implement.md").exists()

    # Non-bundled artifacts should NOT exist
    assert not (target_dir / ".claude" / "skills" / "fake-driven-testing").exists()
    assert not (target_dir / ".claude" / "agents" / "haiku-devrun").exists()
    assert not (target_dir / ".claude" / "commands" / "local").exists()


def test_sync_hooks_adds_missing_hooks(tmp_path: Path) -> None:
    """_sync_hooks adds missing hooks to settings.json."""
    import json

    from erk.core.claude_settings import (
        ERK_EXIT_PLAN_HOOK_COMMAND,
        ERK_USER_PROMPT_HOOK_COMMAND,
    )

    target_claude_dir = tmp_path / ".claude"
    target_claude_dir.mkdir(parents=True)

    # No settings.json exists yet
    added, _ = _sync_hooks(target_claude_dir)

    # Both hooks should be added
    assert added == 2

    # Verify hooks were written
    settings_path = target_claude_dir / "settings.json"
    assert settings_path.exists()

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "hooks" in settings
    assert "UserPromptSubmit" in settings["hooks"]
    assert "PreToolUse" in settings["hooks"]

    # Verify hook commands
    user_prompt_hooks = settings["hooks"]["UserPromptSubmit"]
    assert any(
        hook.get("command") == ERK_USER_PROMPT_HOOK_COMMAND
        for entry in user_prompt_hooks
        for hook in entry.get("hooks", [])
    )

    pre_tool_hooks = settings["hooks"]["PreToolUse"]
    assert any(
        entry.get("matcher") == "ExitPlanMode"
        and any(
            hook.get("command") == ERK_EXIT_PLAN_HOOK_COMMAND for hook in entry.get("hooks", [])
        )
        for entry in pre_tool_hooks
    )


def test_sync_hooks_preserves_existing_settings(tmp_path: Path) -> None:
    """_sync_hooks preserves existing settings when adding hooks."""
    import json

    target_claude_dir = tmp_path / ".claude"
    target_claude_dir.mkdir(parents=True)

    # Create existing settings with permissions
    existing_settings = {"permissions": {"allow": ["Bash(git:*)"]}}
    settings_path = target_claude_dir / "settings.json"
    settings_path.write_text(json.dumps(existing_settings), encoding="utf-8")

    _sync_hooks(target_claude_dir)

    # Verify existing settings preserved
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "permissions" in settings
    assert "Bash(git:*)" in settings["permissions"]["allow"]
    assert "hooks" in settings


def test_sync_hooks_skips_existing_hooks(tmp_path: Path) -> None:
    """_sync_hooks returns 0 when hooks already exist."""
    import json

    from erk.core.claude_settings import add_erk_hooks

    target_claude_dir = tmp_path / ".claude"
    target_claude_dir.mkdir(parents=True)

    # Create settings with hooks already configured
    settings = add_erk_hooks({})
    settings_path = target_claude_dir / "settings.json"
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    added, _ = _sync_hooks(target_claude_dir)

    # No hooks should be added
    assert added == 0


def test_sync_artifacts_includes_hooks(tmp_path: Path) -> None:
    """sync_artifacts also syncs hooks to settings.json."""
    import json

    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    target_dir = tmp_path / "project"
    target_dir.mkdir()

    nonexistent = tmp_path / "nonexistent"
    with (
        patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_dir),
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=nonexistent),
        patch("erk.artifacts.sync.get_current_version", return_value="1.0.0"),
    ):
        result = sync_artifacts(target_dir, force=False)

    assert result.success is True
    # Should include 2 hooks in the count
    assert result.artifacts_installed == 2

    # Verify hooks were synced
    settings_path = target_dir / ".claude" / "settings.json"
    assert settings_path.exists()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "hooks" in settings


def test_sync_actions_copies_bundled_actions(tmp_path: Path) -> None:
    """_sync_actions copies action directories to target."""
    source_dir = tmp_path / "source"
    actions_dir = source_dir / "actions"

    # Create a bundled action (setup-claude-erk is in BUNDLED_ACTIONS)
    action_path = actions_dir / "setup-claude-erk"
    action_path.mkdir(parents=True)
    (action_path / "action.yml").write_text("name: Setup Claude Erk", encoding="utf-8")

    # Create a non-bundled action (should NOT be synced)
    non_bundled = actions_dir / "check-worker-impl"
    non_bundled.mkdir(parents=True)
    (non_bundled / "action.yml").write_text("name: Check Worker", encoding="utf-8")

    target_dir = tmp_path / "target" / "actions"

    copied, synced = _sync_actions(source_dir, target_dir)

    # Should copy exactly 1 file
    assert copied == 1

    # Bundled action should exist
    assert (target_dir / "setup-claude-erk" / "action.yml").exists()

    # Non-bundled action should NOT exist
    assert not (target_dir / "check-worker-impl").exists()

    # Verify synced artifact has correct key
    assert len(synced) == 1
    assert synced[0].key == "actions/setup-claude-erk"


def test_sync_feature_workflows_copies_specified_workflows(tmp_path: Path) -> None:
    """_sync_feature_workflows copies only specified workflow files."""
    source_dir = tmp_path / "source"
    workflows_dir = source_dir / "workflows"
    workflows_dir.mkdir(parents=True)

    # Create workflows
    (workflows_dir / "dignified-python-review.yml").write_text("name: Review", encoding="utf-8")
    (workflows_dir / "other-workflow.yml").write_text("name: Other", encoding="utf-8")

    target_dir = tmp_path / "target" / "workflows"

    # Only sync dignified-python-review.yml
    workflow_names = frozenset({"dignified-python-review.yml"})
    copied, synced = _sync_feature_workflows(source_dir, target_dir, workflow_names)

    assert copied == 1
    assert (target_dir / "dignified-python-review.yml").exists()
    assert not (target_dir / "other-workflow.yml").exists()

    assert len(synced) == 1
    assert synced[0].key == "workflows/dignified-python-review.yml"


def test_sync_feature_installs_dignified_review(tmp_path: Path) -> None:
    """sync_feature installs dignified-review feature artifacts."""
    # Create bundled .github/ with feature artifacts
    bundled_github = tmp_path / "bundled_github"
    bundled_workflows = bundled_github / "workflows"
    bundled_workflows.mkdir(parents=True)
    (bundled_workflows / "dignified-python-review.yml").write_text("name: Review", encoding="utf-8")

    # Create target directory
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    with (
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=bundled_github),
        patch("erk.artifacts.sync.get_current_version", return_value="1.0.0"),
    ):
        result = sync_feature(target_dir, "dignified-review")

    assert result.success is True
    assert result.feature_name == "dignified-review"
    assert result.artifacts_installed == 1  # 1 workflow only (prompts via exec command)

    # Verify workflow was copied
    assert (target_dir / ".github" / "workflows" / "dignified-python-review.yml").exists()


def test_sync_feature_unknown_feature_fails(tmp_path: Path) -> None:
    """sync_feature returns failure for unknown feature names."""
    result = sync_feature(tmp_path, "unknown-feature")

    assert result.success is False
    assert "Unknown feature" in result.message
    assert result.feature_name == "unknown-feature"


def test_sync_artifacts_includes_actions(tmp_path: Path) -> None:
    """sync_artifacts also syncs bundled actions."""
    # Create bundled .claude/ directory
    bundled_claude = tmp_path / "bundled"
    bundled_claude.mkdir()

    # Create bundled .github/ with actions
    bundled_github = tmp_path / "bundled_github"
    bundled_actions = bundled_github / "actions" / "setup-claude-erk"
    bundled_actions.mkdir(parents=True)
    (bundled_actions / "action.yml").write_text("name: Setup", encoding="utf-8")

    # Create target directory
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    with (
        patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_claude),
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=bundled_github),
        patch("erk.artifacts.sync.get_current_version", return_value="1.0.0"),
    ):
        result = sync_artifacts(target_dir, force=False)

    assert result.success is True
    # 1 action + 2 hooks = 3 artifacts
    assert result.artifacts_installed == 3

    # Verify action was copied
    assert (target_dir / ".github" / "actions" / "setup-claude-erk" / "action.yml").exists()
