"""Tests for Claude permission prompts during init.

Mock Usage Policy:
------------------
This file uses minimal mocking for external boundaries:

1. Global config operations:
   - Uses FakeErkInstallation for dependency injection
   - No mocking required - proper abstraction via ConfigStore interface
   - Tests inject FakeErkInstallation with desired initial state
"""

import json

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_init_offers_claude_permission_when_missing() -> None:
    """Test that init offers to add erk permission when Claude settings exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create Claude settings in repo without erk permission
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        claude_settings_path.write_text(
            json.dumps({"permissions": {"allow": ["Bash(git:*)"]}}),
            encoding="utf-8",
        )

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Accept permission (y), confirm write (y), decline hooks (n), delete backup (y)
        result = runner.invoke(cli, ["init"], obj=test_ctx, input="y\ny\nn\ny\n")

        assert result.exit_code == 0, result.output
        assert "Claude settings found" in result.output
        assert "Bash(erk:*)" in result.output
        assert "Proceed with writing changes?" in result.output
        # Verify permission was added
        updated_settings = json.loads(claude_settings_path.read_text(encoding="utf-8"))
        assert "Bash(erk:*)" in updated_settings["permissions"]["allow"]


def test_init_skips_claude_permission_when_already_configured() -> None:
    """Test that init skips prompt when erk permission already exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create Claude settings WITH erk permission already present
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        claude_settings_path.write_text(
            json.dumps({"permissions": {"allow": ["Bash(erk:*)", "Bash(git:*)"]}}),
            encoding="utf-8",
        )

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should NOT prompt about Claude permission
        assert "Claude settings found" not in result.output


def test_init_skips_claude_permission_when_no_settings() -> None:
    """Test that init skips Claude permission setup when no settings.json exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # No .claude/settings.json file in repo

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should NOT prompt about Claude permission
        assert "Claude settings found" not in result.output


def test_init_handles_declined_claude_permission() -> None:
    """Test that init handles user declining Claude permission gracefully."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create Claude settings in repo without erk permission
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        original_settings = {"permissions": {"allow": ["Bash(git:*)"]}}
        claude_settings_path.write_text(json.dumps(original_settings), encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Decline permission (n), decline hooks (n)
        result = runner.invoke(cli, ["init"], obj=test_ctx, input="n\nn\n")

        assert result.exit_code == 0, result.output
        assert "Skipped" in result.output
        # Verify permission was NOT added
        unchanged_settings = json.loads(claude_settings_path.read_text(encoding="utf-8"))
        assert "Bash(erk:*)" not in unchanged_settings["permissions"]["allow"]


def test_init_handles_declined_write_confirmation() -> None:
    """Test that init handles user declining write confirmation gracefully."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create Claude settings in repo without erk permission
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        original_settings = {"permissions": {"allow": ["Bash(git:*)"]}}
        claude_settings_path.write_text(json.dumps(original_settings), encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Accept permission (y), decline write (n), decline hooks (n)
        result = runner.invoke(cli, ["init"], obj=test_ctx, input="y\nn\nn\n")

        assert result.exit_code == 0, result.output
        assert "Proceed with writing changes?" in result.output
        assert "No changes made to settings.json" in result.output
        # Verify permission was NOT added
        unchanged_settings = json.loads(claude_settings_path.read_text(encoding="utf-8"))
        assert "Bash(erk:*)" not in unchanged_settings["permissions"]["allow"]
