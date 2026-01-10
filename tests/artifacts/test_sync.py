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
    get_bundled_claude_dir,
    get_bundled_github_dir,
    sync_artifacts,
    sync_dignified_review,
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
    # Use a skill that's in BUNDLED_SKILLS (learned-docs)
    skill_dir = bundled_dir / "skills" / "learned-docs"
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
    # 1 skill file (hooks are handled by HooksCapability, not artifact sync)
    assert result.artifacts_installed == 1

    # Verify file was copied
    copied_file = target_dir / ".claude" / "skills" / "learned-docs" / "SKILL.md"
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
    # erk-impl.yml (hooks are handled by HooksCapability, not artifact sync)
    assert result.artifacts_installed == 1

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

    # Create a bundled skill (learned-docs is in BUNDLED_SKILLS)
    bundled_skill = source_dir / "learned-docs"
    bundled_skill.mkdir(parents=True)
    (bundled_skill / "SKILL.md").write_text("# Bundled Skill", encoding="utf-8")

    # Create a non-bundled skill (should NOT be synced)
    non_bundled_skill = source_dir / "some-custom-skill"
    non_bundled_skill.mkdir(parents=True)
    (non_bundled_skill / "SKILL.md").write_text("# Custom Skill", encoding="utf-8")

    target_dir = tmp_path / "target" / "skills"

    copied, _ = _sync_directory_artifacts(source_dir, target_dir, BUNDLED_SKILLS, "skills")

    # Should copy exactly 1 file (the bundled skill)
    assert copied == 1

    # Bundled skill should exist
    assert (target_dir / "learned-docs" / "SKILL.md").exists()

    # Non-bundled skill should NOT exist
    assert not (target_dir / "some-custom-skill").exists()


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


def test_sync_commands_handles_nested_directories(tmp_path: Path) -> None:
    """_sync_commands correctly syncs nested command directories."""
    source_dir = tmp_path / "source" / "commands"

    # Create flat erk command
    erk_commands = source_dir / "erk"
    erk_commands.mkdir(parents=True)
    (erk_commands / "plan-save.md").write_text("# Flat Command", encoding="utf-8")

    # Create nested erk command (e.g., commands/erk/system/impl-execute.md)
    nested_commands = erk_commands / "system"
    nested_commands.mkdir(parents=True)
    (nested_commands / "impl-execute.md").write_text("# Nested Command", encoding="utf-8")

    target_dir = tmp_path / "target" / "commands"

    copied, synced = _sync_commands(source_dir, target_dir)

    # Should copy both files (flat + nested)
    assert copied == 2

    # Flat command should exist
    assert (target_dir / "erk" / "plan-save.md").exists()

    # Nested command should exist
    assert (target_dir / "erk" / "system" / "impl-execute.md").exists()

    # Verify synced artifacts have correct keys with relative paths
    synced_keys = {s.key for s in synced}
    assert "commands/erk/plan-save.md" in synced_keys
    assert "commands/erk/system/impl-execute.md" in synced_keys


def test_sync_artifacts_filters_all_artifact_types(tmp_path: Path) -> None:
    """Full integration test: sync_artifacts filters skills, agents, and commands."""
    bundled_claude = tmp_path / "bundled"

    # Create bundled skills (learned-docs is in BUNDLED_SKILLS)
    bundled_skill = bundled_claude / "skills" / "learned-docs"
    bundled_skill.mkdir(parents=True)
    (bundled_skill / "SKILL.md").write_text("# Bundled", encoding="utf-8")

    # Create non-bundled skill (should NOT be synced)
    non_bundled_skill = bundled_claude / "skills" / "some-custom-skill"
    non_bundled_skill.mkdir(parents=True)
    (non_bundled_skill / "SKILL.md").write_text("# Custom", encoding="utf-8")

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
    # Should copy: 1 skill + 1 agent + 1 command (hooks handled by HooksCapability)
    assert result.artifacts_installed == 3

    # Bundled artifacts should exist
    assert (target_dir / ".claude" / "skills" / "learned-docs" / "SKILL.md").exists()
    assert (target_dir / ".claude" / "agents" / "devrun" / "AGENT.md").exists()
    assert (target_dir / ".claude" / "commands" / "erk" / "plan-implement.md").exists()

    # Non-bundled artifacts should NOT exist
    assert not (target_dir / ".claude" / "skills" / "some-custom-skill").exists()
    assert not (target_dir / ".claude" / "agents" / "haiku-devrun").exists()
    assert not (target_dir / ".claude" / "commands" / "local").exists()


def test_sync_artifacts_syncs_installed_capabilities(tmp_path: Path) -> None:
    """sync_artifacts updates installed capabilities.

    After syncing file-based artifacts, sync_artifacts iterates through
    installed capabilities and calls install() to ensure they're up-to-date.
    """
    import json

    from erk.core.claude_settings import add_erk_hooks

    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    target_dir = tmp_path / "project"
    target_dir.mkdir()

    # Pre-install hooks (simulates HooksCapability already installed)
    settings_path = target_dir / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings = add_erk_hooks({})
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    nonexistent = tmp_path / "nonexistent"
    with (
        patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_dir),
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=nonexistent),
        patch("erk.artifacts.sync.get_current_version", return_value="1.0.0"),
    ):
        result = sync_artifacts(target_dir, force=False)

    assert result.success is True
    # Hooks are managed by capability, not counted as file artifacts
    assert result.artifacts_installed == 0

    # Verify hooks still exist (capability install() is idempotent)
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "hooks" in settings
    assert "UserPromptSubmit" in settings["hooks"]


def test_sync_actions_copies_bundled_actions(tmp_path: Path) -> None:
    """_sync_actions copies action directories to target."""
    source_dir = tmp_path / "source"
    actions_dir = source_dir / "actions"

    # Create bundled actions (both are in BUNDLED_ACTIONS)
    action_erk = actions_dir / "setup-claude-erk"
    action_erk.mkdir(parents=True)
    (action_erk / "action.yml").write_text("name: Setup Claude Erk", encoding="utf-8")

    action_code = actions_dir / "setup-claude-code"
    action_code.mkdir(parents=True)
    (action_code / "action.yml").write_text("name: Setup Claude Code", encoding="utf-8")

    # Create a non-bundled action (should NOT be synced)
    non_bundled = actions_dir / "check-worker-impl"
    non_bundled.mkdir(parents=True)
    (non_bundled / "action.yml").write_text("name: Check Worker", encoding="utf-8")

    target_dir = tmp_path / "target" / "actions"

    copied, synced = _sync_actions(source_dir, target_dir)

    # Should copy exactly 2 files (both bundled actions)
    assert copied == 2

    # Both bundled actions should exist
    assert (target_dir / "setup-claude-erk" / "action.yml").exists()
    assert (target_dir / "setup-claude-code" / "action.yml").exists()

    # Non-bundled action should NOT exist
    assert not (target_dir / "check-worker-impl").exists()

    # Verify synced artifacts have correct keys
    assert len(synced) == 2
    synced_keys = {s.key for s in synced}
    assert synced_keys == {"actions/setup-claude-erk", "actions/setup-claude-code"}


def test_sync_artifacts_includes_actions(tmp_path: Path) -> None:
    """sync_artifacts also syncs bundled actions."""
    # Create bundled .claude/ directory
    bundled_claude = tmp_path / "bundled"
    bundled_claude.mkdir()

    # Create bundled .github/ with both bundled actions
    bundled_github = tmp_path / "bundled_github"
    action_erk = bundled_github / "actions" / "setup-claude-erk"
    action_erk.mkdir(parents=True)
    (action_erk / "action.yml").write_text("name: Setup Erk", encoding="utf-8")

    action_code = bundled_github / "actions" / "setup-claude-code"
    action_code.mkdir(parents=True)
    (action_code / "action.yml").write_text("name: Setup Code", encoding="utf-8")

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
    # 2 actions (hooks are handled by HooksCapability, not artifact sync)
    assert result.artifacts_installed == 2

    # Verify both actions were copied
    assert (target_dir / ".github" / "actions" / "setup-claude-erk" / "action.yml").exists()
    assert (target_dir / ".github" / "actions" / "setup-claude-code" / "action.yml").exists()


def test_sync_dignified_review_copies_all_artifacts(tmp_path: Path) -> None:
    """sync_dignified_review copies skill, workflow, and prompt."""
    # Create bundled .claude/ with dignified-python skill
    bundled_claude = tmp_path / "bundled_claude"
    skill_dir = bundled_claude / "skills" / "dignified-python"
    skill_dir.mkdir(parents=True)
    (skill_dir / "dignified-python.md").write_text("# Skill", encoding="utf-8")
    (skill_dir / "dignified-python-core.md").write_text("# Core", encoding="utf-8")

    # Create bundled .github/ with workflow and prompt
    bundled_github = tmp_path / "bundled_github"
    workflow_dir = bundled_github / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "dignified-python-review.yml").write_text("name: Review", encoding="utf-8")

    prompt_dir = bundled_github / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "dignified-python-review.md").write_text("# Prompt", encoding="utf-8")

    # Create target directory
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    with (
        patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_claude),
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=bundled_github),
    ):
        result = sync_dignified_review(target_dir)

    assert result.success is True
    # 2 skill files + 1 workflow + 1 prompt = 4 files
    assert result.artifacts_installed == 4
    assert "dignified-review" in result.message

    # Verify skill was copied
    assert (target_dir / ".claude" / "skills" / "dignified-python" / "dignified-python.md").exists()
    assert (
        target_dir / ".claude" / "skills" / "dignified-python" / "dignified-python-core.md"
    ).exists()

    # Verify workflow was copied
    workflow_path = target_dir / ".github" / "workflows" / "dignified-python-review.yml"
    assert workflow_path.exists()
    assert workflow_path.read_text(encoding="utf-8") == "name: Review"

    # Verify prompt was copied
    prompt_path = target_dir / ".github" / "prompts" / "dignified-python-review.md"
    assert prompt_path.exists()
    assert prompt_path.read_text(encoding="utf-8") == "# Prompt"


def test_sync_dignified_review_handles_missing_sources(tmp_path: Path) -> None:
    """sync_dignified_review succeeds with 0 files when sources don't exist."""
    # Create empty bundled directories
    bundled_claude = tmp_path / "bundled_claude"
    bundled_claude.mkdir()

    bundled_github = tmp_path / "bundled_github"
    bundled_github.mkdir()

    target_dir = tmp_path / "project"
    target_dir.mkdir()

    with (
        patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_claude),
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=bundled_github),
    ):
        result = sync_dignified_review(target_dir)

    assert result.success is True
    assert result.artifacts_installed == 0


def test_sync_artifacts_in_erk_repo_tracks_nested_commands(tmp_path: Path) -> None:
    """sync_artifacts in erk repo correctly tracks nested commands."""
    # Create pyproject.toml to simulate erk repo
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "erk"\n', encoding="utf-8")

    # Create bundled commands with nested structure
    bundled_claude = tmp_path / ".claude"
    bundled_cmd = bundled_claude / "commands" / "erk"
    bundled_cmd.mkdir(parents=True)
    (bundled_cmd / "plan-save.md").write_text("# Flat Command", encoding="utf-8")

    # Create nested command (e.g., commands/erk/system/impl-execute.md)
    nested_cmd = bundled_cmd / "system"
    nested_cmd.mkdir(parents=True)
    (nested_cmd / "impl-execute.md").write_text("# Nested Command", encoding="utf-8")

    with (
        patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_claude),
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=tmp_path / ".github"),
        patch("erk.artifacts.sync.get_current_version", return_value="1.0.0"),
    ):
        result = sync_artifacts(tmp_path, force=False)

    assert result.success is True
    # Should be development mode (no files actually copied)
    assert result.artifacts_installed == 0
    assert "Development mode" in result.message

    # Verify state.toml was created with nested command keys
    state_file = tmp_path / ".erk" / "state.toml"
    assert state_file.exists()
    content = state_file.read_text(encoding="utf-8")

    # Both flat and nested commands should be tracked
    assert "commands/erk/plan-save.md" in content
    assert "commands/erk/system/impl-execute.md" in content
