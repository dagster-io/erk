"""Tests for hooks auto-installation and artifact sync during init.

Mock Usage Policy:
------------------
This file uses minimal mocking for external boundaries:

1. os.environ HOME patches:
   - LEGITIMATE: Testing path resolution logic that depends on $HOME
   - The init command uses Path.home() to determine ~/.erk location
   - Patching HOME redirects to temp directory for test isolation
   - Cannot be replaced with fakes (environment variable is external boundary)

2. Global config operations:
   - Uses FakeErkInstallation for dependency injection
   - No mocking required - proper abstraction via ConfigStore interface
   - Tests inject FakeErkInstallation with desired initial state

3. sync_artifacts mocking:
   - LEGITIMATE: Testing CLI's response to sync results
   - The sync logic is tested separately in artifact tests
   - Here we test that init handles success/failure appropriately
"""

import json
import os
from unittest import mock

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_init_installs_hooks_automatically() -> None:
    """Test that init automatically installs hooks during initialization.

    Hooks may be installed either by artifact sync or as a required capability,
    depending on timing. This test verifies hooks are installed regardless of
    which mechanism does it.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create empty Claude settings (no hooks)
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        claude_settings_path.write_text("{}", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Run init with --no-interactive to skip interactive prompts
        # HOME must be set for statusline setup to work
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        # Verify hooks were added (either by artifact sync or required capability)
        updated_settings = json.loads(claude_settings_path.read_text(encoding="utf-8"))
        assert "hooks" in updated_settings
        assert "UserPromptSubmit" in updated_settings["hooks"]
        assert "PreToolUse" in updated_settings["hooks"]


def test_init_skips_hooks_when_already_installed() -> None:
    """Test that init skips hook installation when hooks already exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create Claude settings WITH erk hooks already present
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        existing_settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    "ERK_HOOK_ID=user-prompt-hook erk exec user-prompt-hook"
                                ),
                            }
                        ],
                    }
                ],
                "PreToolUse": [
                    {
                        "matcher": "ExitPlanMode",
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    "ERK_HOOK_ID=exit-plan-mode-hook erk exec exit-plan-mode-hook"
                                ),
                            }
                        ],
                    }
                ],
            }
        }
        claude_settings_path.write_text(json.dumps(existing_settings), encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Run init - hooks should not be re-installed
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should NOT see "Added erk hooks" since they already exist
        assert "Added erk hooks" not in result.output


def test_init_creates_settings_json_for_hooks() -> None:
    """Test that init creates .claude/settings.json if missing when installing hooks."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # No .claude/settings.json file
        claude_settings_path = env.cwd / ".claude" / "settings.json"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Run init - should create settings.json with hooks
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        # Verify file was created with hooks
        assert claude_settings_path.exists()
        created_settings = json.loads(claude_settings_path.read_text(encoding="utf-8"))
        assert "hooks" in created_settings


def test_init_hooks_flag_removed() -> None:
    """Test that the --hooks flag no longer exists.

    The --hooks flag was removed because hooks are now a required capability
    that is auto-installed during init.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Try using the old --hooks flag
        result = runner.invoke(cli, ["init", "--hooks"], obj=test_ctx)

        # Should fail because --hooks no longer exists
        assert result.exit_code != 0
        assert "No such option" in result.output or "no such option" in result.output.lower()


def test_init_syncs_artifacts_successfully() -> None:
    """Test that init calls sync_artifacts and shows success message."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Mock sync_artifacts to return success
        from erk.artifacts.sync import SyncResult

        with mock.patch("erk.cli.commands.init.main.sync_artifacts") as mock_sync:
            mock_sync.return_value = SyncResult(
                success=True, artifacts_installed=5, message="Synced 5 artifact files"
            )

            result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

            assert result.exit_code == 0, result.output
            # Verify sync_artifacts was called with correct arguments
            mock_sync.assert_called_once_with(env.cwd, force=False)
            # Verify success message appears in output
            assert "✓" in result.output
            assert "Synced 5 artifact files" in result.output


def test_init_shows_warning_on_artifact_sync_failure() -> None:
    """Test that init shows warning but continues when artifact sync fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Mock sync_artifacts to return failure
        from erk.artifacts.sync import SyncResult

        with mock.patch("erk.cli.commands.init.main.sync_artifacts") as mock_sync:
            mock_sync.return_value = SyncResult(
                success=False, artifacts_installed=0, message="Bundled .claude/ not found"
            )

            result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

            # Init should continue despite sync failure (non-fatal)
            assert result.exit_code == 0, result.output
            # Verify sync_artifacts was called
            mock_sync.assert_called_once_with(env.cwd, force=False)
            # Verify warning appears in output
            assert "⚠" in result.output
            assert "Artifact sync failed" in result.output
            assert "Bundled .claude/ not found" in result.output
            assert "Run 'erk artifact sync' to retry" in result.output
