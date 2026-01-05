"""Tests for shell detection, completion, and confirmation during init.

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
"""

import os
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_init_first_time_offers_shell_setup() -> None:
    """Test that first-time init offers shell integration setup."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Provide input: erk_root, decline hooks, decline shell setup
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\nn\n")

        assert result.exit_code == 0, result.output
        # Should mention shell integration
        assert "shell integration" in result.output.lower()


def test_init_shell_flag_only_setup() -> None:
    """Test that --shell flag only performs shell setup."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Decline shell setup
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--shell"], obj=test_ctx, input="n\n")

        assert result.exit_code == 0, result.output
        # Should mention shell but not create config
        repo_dir = erk_root / "repos" / env.cwd.name
        config_path = repo_dir / "config.toml"
        assert not config_path.exists()


def test_init_detects_bash_shell() -> None:
    """Test that init correctly detects bash shell."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Input: erk_root, decline hooks, decline shell
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\nn\n",
            )

        assert result.exit_code == 0, result.output
        assert "bash" in result.output.lower()


def test_init_detects_zsh_shell() -> None:
    """Test that init correctly detects zsh shell."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        zshrc = Path.home() / ".zshrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("zsh", zshrc)),
            dry_run=False,
        )

        # Input: erk_root, decline hooks, decline shell
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\nn\n",
            )

        assert result.exit_code == 0, result.output
        assert "zsh" in result.output.lower()


def test_init_detects_fish_shell() -> None:
    """Test that init correctly detects fish shell."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        fish_config = Path.home() / ".config" / "fish" / "config.fish"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("fish", fish_config)),
            dry_run=False,
        )

        # Input: erk_root, decline hooks, decline shell
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\nn\n",
            )

        assert result.exit_code == 0, result.output
        assert "fish" in result.output.lower()


def test_init_skips_unknown_shell() -> None:
    """Test that init skips shell setup for unknown shells."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        # Input: erk_root, decline hooks (no shell prompt - unknown shell)
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Unable to detect shell" in result.output


def test_init_prints_completion_instructions() -> None:
    """Test that init prints completion instructions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Input: erk_root, decline hooks, accept shell, accept config save
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\ny\ny\n",
            )

        assert result.exit_code == 0, result.output
        # Verify instructions are printed, not file written
        assert "Shell Integration Setup" in result.output
        assert "# Erk completion" in result.output
        assert "source <(erk completion bash)" in result.output


def test_init_prints_wrapper_instructions() -> None:
    """Test that init prints wrapper function instructions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Input: erk_root, decline hooks, accept shell, accept config save
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\ny\ny\n",
            )

        assert result.exit_code == 0, result.output
        # Verify wrapper instructions are printed
        assert "Shell Integration Setup" in result.output
        assert "# Erk shell integration" in result.output
        assert "erk()" in result.output


def test_init_skips_shell_if_declined() -> None:
    """Test that init skips shell setup if user declines."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Input: erk_root, decline hooks, decline shell
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\nn\n",
            )

        assert result.exit_code == 0, result.output
        # Verify no instructions were printed when declined
        assert "Shell Integration Setup" not in result.output
        assert "Skipping shell integration" in result.output


def test_shell_setup_confirmation_declined_with_shell_flag() -> None:
    """Test user declining confirmation for global config write (--shell flag)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Answer "y" to shell setup, then "n" to config write confirmation
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--shell"], obj=test_ctx, input="y\nn\n")

        assert result.exit_code == 0, result.output
        assert "Shell integration instructions shown above" in result.output
        assert "Run 'erk init --shell' to save this preference" in result.output
        # Config should NOT have been updated
        loaded = erk_installation.load_config()
        assert loaded.shell_setup_complete is False


def test_shell_setup_confirmation_accepted_with_shell_flag() -> None:
    """Test user accepting confirmation for global config write (--shell flag)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Answer "y" to shell setup, then "y" to config write confirmation
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--shell"], obj=test_ctx, input="y\ny\n")

        assert result.exit_code == 0, result.output
        assert "✓ Global config updated" in result.output
        # Config should have been updated
        loaded = erk_installation.load_config()
        assert loaded.shell_setup_complete is True


def test_shell_setup_confirmation_declined_first_init() -> None:
    """Test user declining confirmation during first-time init."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Input: erk_root, decline hooks, accept shell, decline config save
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\ny\nn\n")

        assert result.exit_code == 0, result.output
        assert "Shell integration instructions shown above" in result.output
        # Config should exist (created by first-time init)
        assert erk_installation.config_exists()
        # But shell_setup_complete should be False (user declined)
        loaded = erk_installation.load_config()
        assert loaded.shell_setup_complete is False


def test_shell_setup_permission_error_with_shell_flag() -> None:
    """Test permission error handling when saving global config (--shell flag)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        # Create an ErkInstallation that raises PermissionError on save
        class PermissionErrorErkInstallation(FakeErkInstallation):
            def save_config(self, config: GlobalConfig) -> None:
                raise PermissionError(
                    f"Cannot write to file: {self.config_path()}\n"
                    "The file exists but is not writable.\n\n"
                    "To fix this manually:\n"
                    f"  1. Make it writable: chmod 644 {self.config_path()}\n"
                    "  2. Run erk init --shell again"
                )

        erk_installation = PermissionErrorErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Answer "y" to shell setup, then "y" to config write confirmation
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--shell"], obj=test_ctx, input="y\ny\n")

        assert result.exit_code == 1, result.output
        assert "❌ Error: Could not save global config" in result.output
        assert "Cannot write to file" in result.output
        assert "Shell integration instructions shown above" in result.output
        assert "You can use them now - erk just couldn't save" in result.output


def test_shell_setup_permission_error_first_init() -> None:
    """Test permission error handling during first-time init (doesn't exit)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        # Create an ErkInstallation that allows first save but fails on second
        class ConditionalPermissionErrorErkInstallation(FakeErkInstallation):
            def __init__(self) -> None:
                super().__init__(config=None)
                self.save_count = 0

            def save_config(self, config: GlobalConfig) -> None:
                self.save_count += 1
                if self.save_count == 1:
                    # First save (creating global config) succeeds
                    super().save_config(config)
                else:
                    # Second save (shell setup update) fails
                    raise PermissionError(
                        f"Cannot write to file: {self.config_path()}\n"
                        "Permission denied during write operation."
                    )

        erk_installation = ConditionalPermissionErrorErkInstallation()

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Input: erk_root, decline hooks, accept shell, accept config save
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\ny\ny\n")

        # Should NOT exit with error code (first-time init continues)
        assert result.exit_code == 0, result.output
        assert "❌ Error: Could not save global config" in result.output
        assert "Cannot write to file" in result.output
        assert "Shell integration instructions shown above" in result.output
        # First save succeeded, second failed
        assert erk_installation.save_count == 2
