"""Tests for health_checks module."""

import json
from pathlib import Path

import pytest

from erk.core.health_checks import (
    CheckResult,
    check_claude_settings,
    check_erk_version,
    check_gitignore_entries,
    check_hooks_disabled,
    check_managed_artifacts,
    check_post_plan_implement_ci_hook,
    check_repository,
    check_uv_version,
)
from erk.core.health_checks_dogfooder.legacy_config_locations import (
    check_legacy_config_locations,
)
from erk_shared.extraction.claude_installation import FakeClaudeInstallation
from erk_shared.git.fake import FakeGit
from tests.fakes.context import create_test_context
from tests.fakes.shell import FakeShell


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

    assert result.name == "claude-settings"
    assert result.passed is True
    assert "No .claude/settings.json" in result.message


def test_check_claude_settings_valid_json(tmp_path: Path) -> None:
    """Test claude settings check with valid settings file."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings_file = claude_dir / "settings.json"
    settings_file.write_text(json.dumps({"hooks": {}}), encoding="utf-8")

    result = check_claude_settings(tmp_path)

    assert result.name == "claude-settings"
    assert result.passed is True
    assert "looks valid" in result.message.lower() or "using defaults" in result.message.lower()


def test_check_claude_settings_invalid_json(tmp_path: Path) -> None:
    """Test claude settings check raises JSONDecodeError for invalid JSON."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings_file = claude_dir / "settings.json"
    settings_file.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        check_claude_settings(tmp_path)


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

    assert result.name == "claude-settings"
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
    shell = FakeShell(installed_tools={})

    result = check_uv_version(shell)

    assert result.name == "uv"
    assert result.passed is False
    assert "not found in PATH" in result.message
    assert result.details is not None
    assert "https://docs.astral.sh/uv" in result.details


def test_check_uv_version_available() -> None:
    """Test check_uv_version when uv is installed."""
    shell = FakeShell(
        installed_tools={"uv": "/usr/bin/uv"},
        tool_versions={"uv": "uv 0.9.2"},
    )

    result = check_uv_version(shell)

    assert result.name == "uv"
    assert result.passed is True
    assert "0.9.2" in result.message
    assert result.details is not None
    assert "uv self update" in result.details


def test_check_uv_version_with_build_info() -> None:
    """Test check_uv_version parses version with build info."""
    shell = FakeShell(
        installed_tools={"uv": "/usr/bin/uv"},
        tool_versions={"uv": "uv 0.9.2 (Homebrew 2025-10-10)"},
    )

    result = check_uv_version(shell)

    assert result.name == "uv"
    assert result.passed is True
    assert "0.9.2" in result.message
    # Should NOT include the build info in version
    assert "Homebrew" not in result.message


# --- Hooks Disabled Check Tests ---


def test_check_hooks_disabled_no_files() -> None:
    """Test when no settings files exist."""
    installation = FakeClaudeInstallation.for_test()

    result = check_hooks_disabled(installation)

    assert result.name == "claude-hooks"
    assert result.passed is True
    assert result.warning is False
    assert "enabled" in result.message.lower()


def test_check_hooks_disabled_in_settings() -> None:
    """Test when hooks.disabled=true in settings.json."""
    installation = FakeClaudeInstallation.for_test(settings={"hooks": {"disabled": True}})

    result = check_hooks_disabled(installation)

    assert result.name == "claude-hooks"
    assert result.passed is True
    assert result.warning is True
    assert "settings.json" in result.message


def test_check_hooks_disabled_in_local(tmp_path: Path) -> None:
    """Test when hooks.disabled=true in settings.local.json.

    Note: local settings file is still checked via filesystem for now,
    so we need to create the file for this test.
    """
    installation = FakeClaudeInstallation.for_test(local_settings={"hooks": {"disabled": True}})

    # For now, the local settings check still reads from filesystem
    # This test verifies the fake doesn't break when local_settings is set
    result = check_hooks_disabled(installation)

    # Since the fake returns a non-existent path for get_local_settings_path,
    # the local file won't be found
    assert result.name == "claude-hooks"
    assert result.passed is True


def test_check_hooks_disabled_false() -> None:
    """Test when hooks.disabled=false (explicitly enabled)."""
    installation = FakeClaudeInstallation.for_test(settings={"hooks": {"disabled": False}})

    result = check_hooks_disabled(installation)

    assert result.name == "claude-hooks"
    assert result.passed is True
    assert result.warning is False


def test_check_hooks_disabled_no_hooks_key() -> None:
    """Test when settings exist but no hooks key."""
    installation = FakeClaudeInstallation.for_test(settings={"other_key": "value"})

    result = check_hooks_disabled(installation)

    assert result.name == "claude-hooks"
    assert result.passed is True
    assert result.warning is False


# --- CheckResult warning field tests ---


def test_check_result_with_warning() -> None:
    """Test CheckResult with warning=True."""
    result = CheckResult(
        name="test",
        passed=True,
        message="Test warning",
        warning=True,
    )

    assert result.name == "test"
    assert result.passed is True
    assert result.warning is True
    assert result.message == "Test warning"
    assert result.details is None


def test_check_result_warning_defaults_false() -> None:
    """Test CheckResult warning defaults to False."""
    result = CheckResult(
        name="test",
        passed=True,
        message="Test passed",
    )

    assert result.warning is False


# --- Legacy Config Location Tests ---


def test_check_legacy_config_primary_location_exists(tmp_path: Path) -> None:
    """Test legacy config check when primary location (.erk/config.toml) exists."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    (erk_dir / "config.toml").write_text("[env]", encoding="utf-8")

    result = check_legacy_config_locations(tmp_path, None)

    assert result.name == "legacy-config"
    assert result.passed is True
    assert result.warning is False
    assert "primary location" in result.message


def test_check_legacy_config_no_legacy_configs(tmp_path: Path) -> None:
    """Test legacy config check when no legacy configs exist."""
    # No configs anywhere
    result = check_legacy_config_locations(tmp_path, None)

    assert result.name == "legacy-config"
    assert result.passed is True
    assert result.warning is False
    assert "No legacy config files found" in result.message


def test_check_legacy_config_repo_root_legacy(tmp_path: Path) -> None:
    """Test legacy config check when legacy config at repo root exists."""
    # Create legacy config at repo root
    (tmp_path / "config.toml").write_text("[env]", encoding="utf-8")

    result = check_legacy_config_locations(tmp_path, None)

    assert result.name == "legacy-config"
    assert result.passed is True  # Warning only
    assert result.warning is True
    assert "1 legacy config file(s)" in result.message
    assert result.details is not None
    assert "repo root" in result.details
    assert str(tmp_path / ".erk" / "config.toml") in result.details


def test_check_legacy_config_metadata_dir_legacy(tmp_path: Path) -> None:
    """Test legacy config check when legacy config in metadata dir exists."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    # Create legacy config in metadata dir
    (metadata_dir / "config.toml").write_text("[env]", encoding="utf-8")

    result = check_legacy_config_locations(repo_root, metadata_dir)

    assert result.name == "legacy-config"
    assert result.passed is True  # Warning only
    assert result.warning is True
    assert "1 legacy config file(s)" in result.message
    assert result.details is not None
    assert "metadata dir" in result.details


def test_check_legacy_config_both_legacy_locations(tmp_path: Path) -> None:
    """Test legacy config check when both legacy locations have configs."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    # Create legacy configs in both locations
    (repo_root / "config.toml").write_text("[env]", encoding="utf-8")
    (metadata_dir / "config.toml").write_text("[env]", encoding="utf-8")

    result = check_legacy_config_locations(repo_root, metadata_dir)

    assert result.name == "legacy-config"
    assert result.passed is True  # Warning only
    assert result.warning is True
    assert "2 legacy config file(s)" in result.message
    assert result.details is not None
    # Both locations mentioned
    assert "repo root" in result.details
    assert "metadata dir" in result.details


def test_check_legacy_config_ignores_legacy_when_primary_exists(tmp_path: Path) -> None:
    """Test that legacy configs are ignored when primary location exists."""
    # Create primary config
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    (erk_dir / "config.toml").write_text("[env]", encoding="utf-8")
    # Also create legacy config at repo root
    (tmp_path / "config.toml").write_text("[env]", encoding="utf-8")

    result = check_legacy_config_locations(tmp_path, None)

    # Should report primary location, not warn about legacy
    assert result.name == "legacy-config"
    assert result.passed is True
    assert result.warning is False
    assert "primary location" in result.message


# --- Managed Artifacts Tests ---


def test_check_managed_artifacts_no_claude_dir(tmp_path: Path) -> None:
    """Test managed artifacts check when no .claude/ directory exists."""
    result = check_managed_artifacts(tmp_path)

    assert result.name == "managed-artifacts"
    assert result.passed is True
    assert result.warning is False
    assert "No .claude/ directory" in result.message


def test_check_managed_artifacts_in_erk_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test managed artifacts check in erk repo → shows counts from source."""
    import json

    from erk.core.claude_settings import add_erk_hooks

    # Create pyproject.toml that makes it look like erk repo
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('name = "erk"\nversion = "1.0.0"', encoding="utf-8")

    # Create bundled dir with command
    bundled_dir = tmp_path / "bundled" / ".claude"
    bundled_commands = bundled_dir / "commands" / "erk"
    bundled_commands.mkdir(parents=True)
    (bundled_commands / "plan-save.md").write_text("# Command", encoding="utf-8")

    # Create project dir WITH the command and hooks
    project_claude = tmp_path / ".claude"
    project_commands = project_claude / "commands" / "erk"
    project_commands.mkdir(parents=True)
    (project_commands / "plan-save.md").write_text("# Command", encoding="utf-8")
    settings = add_erk_hooks({})
    (project_claude / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    monkeypatch.setattr("erk.artifacts.artifact_health.get_bundled_claude_dir", lambda: bundled_dir)
    monkeypatch.setattr(
        "erk.artifacts.artifact_health.get_bundled_github_dir",
        lambda: tmp_path / "bundled" / ".github",
    )

    result = check_managed_artifacts(tmp_path)

    assert result.name == "managed-artifacts"
    assert result.passed is True
    assert "from source" in result.message
    # Should show artifact type summary in details
    assert result.details is not None
    assert "commands" in result.details or "hooks" in result.details


def test_check_managed_artifacts_produces_type_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test managed artifacts check produces per-type summary."""
    import json

    from erk.core.claude_settings import add_erk_hooks

    # Create bundled dir with command (minimal setup)
    bundled_dir = tmp_path / "bundled" / ".claude"
    bundled_commands = bundled_dir / "commands" / "erk"
    bundled_commands.mkdir(parents=True)
    (bundled_commands / "plan-save.md").write_text("# Command", encoding="utf-8")

    # Create project dir WITH the command and hooks
    project_dir = tmp_path / "project"
    project_claude = project_dir / ".claude"
    project_commands = project_claude / "commands" / "erk"
    project_commands.mkdir(parents=True)
    (project_commands / "plan-save.md").write_text("# Command", encoding="utf-8")
    # Add hooks so all bundled artifacts are present
    settings = add_erk_hooks({})
    (project_claude / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    monkeypatch.setattr("erk.artifacts.artifact_health.get_bundled_claude_dir", lambda: bundled_dir)
    monkeypatch.setattr(
        "erk.artifacts.artifact_health.get_bundled_github_dir",
        lambda: tmp_path / "bundled" / ".github",
    )
    monkeypatch.setattr("erk.core.health_checks.is_in_erk_repo", lambda _: False)

    result = check_managed_artifacts(project_dir)

    assert result.name == "managed-artifacts"
    # The check runs and produces details with type summary
    assert result.details is not None
    # Should contain type names (skills may show as not-installed since we didn't mock them)
    assert "commands" in result.details or "hooks" in result.details


def test_check_managed_artifacts_some_not_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test managed artifacts check when some artifacts are not installed."""
    import json

    from erk.core.claude_settings import add_erk_hooks

    # Create bundled dir with command
    bundled_dir = tmp_path / "bundled" / ".claude"
    bundled_commands = bundled_dir / "commands" / "erk"
    bundled_commands.mkdir(parents=True)
    (bundled_commands / "plan-save.md").write_text("# Command", encoding="utf-8")
    (bundled_commands / "plan-implement.md").write_text("# Command 2", encoding="utf-8")

    # Create project dir with only ONE command (missing the other)
    project_dir = tmp_path / "project"
    project_claude = project_dir / ".claude"
    project_commands = project_claude / "commands" / "erk"
    project_commands.mkdir(parents=True)
    (project_commands / "plan-save.md").write_text("# Command", encoding="utf-8")
    # plan-implement.md is NOT installed
    settings = add_erk_hooks({})
    (project_claude / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    monkeypatch.setattr("erk.artifacts.artifact_health.get_bundled_claude_dir", lambda: bundled_dir)
    monkeypatch.setattr(
        "erk.artifacts.artifact_health.get_bundled_github_dir",
        lambda: tmp_path / "bundled" / ".github",
    )
    monkeypatch.setattr("erk.core.health_checks.is_in_erk_repo", lambda _: False)

    result = check_managed_artifacts(project_dir)

    assert result.name == "managed-artifacts"
    assert result.passed is False  # not-installed causes failure
    assert "have issues" in result.message
    assert result.details is not None
    assert "commands" in result.details
    assert "erk artifact sync" in result.details


def test_check_managed_artifacts_shows_type_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test managed artifacts shows per-type summary in details."""
    import json

    from erk.core.claude_settings import add_erk_hooks

    # Create bundled dir with command and skill
    bundled_dir = tmp_path / "bundled" / ".claude"
    bundled_commands = bundled_dir / "commands" / "erk"
    bundled_commands.mkdir(parents=True)
    (bundled_commands / "plan-save.md").write_text("# Command", encoding="utf-8")
    bundled_skills = bundled_dir / "skills" / "dignified-python"
    bundled_skills.mkdir(parents=True)
    (bundled_skills / "core.md").write_text("# Core", encoding="utf-8")

    # Create project dir with both artifacts
    project_dir = tmp_path / "project"
    project_claude = project_dir / ".claude"
    project_commands = project_claude / "commands" / "erk"
    project_commands.mkdir(parents=True)
    (project_commands / "plan-save.md").write_text("# Command", encoding="utf-8")
    project_skills = project_claude / "skills" / "dignified-python"
    project_skills.mkdir(parents=True)
    (project_skills / "core.md").write_text("# Core", encoding="utf-8")
    settings = add_erk_hooks({})
    (project_claude / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    monkeypatch.setattr("erk.artifacts.artifact_health.get_bundled_claude_dir", lambda: bundled_dir)
    monkeypatch.setattr(
        "erk.artifacts.artifact_health.get_bundled_github_dir",
        lambda: tmp_path / "bundled" / ".github",
    )
    monkeypatch.setattr("erk.core.health_checks.is_in_erk_repo", lambda _: False)

    result = check_managed_artifacts(project_dir)

    assert result.name == "managed-artifacts"
    assert result.details is not None
    # Check for type summary in details
    assert "skills" in result.details
    assert "commands" in result.details
    assert "hooks" in result.details


# --- Post-Plan-Implement CI Hook Tests ---


def test_check_post_plan_implement_ci_hook_exists(tmp_path: Path) -> None:
    """Test CI hook check when hook file exists."""
    hook_dir = tmp_path / ".erk" / "prompt-hooks"
    hook_dir.mkdir(parents=True)
    (hook_dir / "post-plan-implement-ci.md").write_text("# CI instructions", encoding="utf-8")

    result = check_post_plan_implement_ci_hook(tmp_path)

    assert result.name == "post-plan-implement-ci-hook"
    assert result.passed is True
    assert result.info is False  # Green check, not info
    assert "CI instructions hook configured" in result.message
    assert ".erk/prompt-hooks/post-plan-implement-ci.md" in result.message
    assert result.details is None


def test_check_post_plan_implement_ci_hook_missing(tmp_path: Path) -> None:
    """Test CI hook check when hook file is missing."""
    result = check_post_plan_implement_ci_hook(tmp_path)

    assert result.name == "post-plan-implement-ci-hook"
    assert result.passed is True
    assert result.info is True
    assert "No CI instructions hook" in result.message
    assert ".erk/prompt-hooks/post-plan-implement-ci.md" in result.message
    assert result.details is not None
    assert "post-plan-implement-ci.md" in result.details
    assert "CI instructions" in result.details
