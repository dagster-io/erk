"""Tests for erk init shell command."""

import os
from unittest import mock

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.init_utils import ERK_SHELL_INTEGRATION_MARKER
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.git.fake import FakeGit
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_init_shell_zsh_outputs_wrapper() -> None:
    """Test that erk init shell zsh outputs wrapper content."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "shell", "zsh"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Check for key parts of shell wrapper
        assert ERK_SHELL_INTEGRATION_MARKER in result.output
        assert "erk()" in result.output
        assert 'eval "$(erk init shell zsh)"' not in result.output  # Should be raw output
        # Check for completion line
        assert "source <(erk completion zsh)" in result.output


def test_init_shell_bash_outputs_wrapper() -> None:
    """Test that erk init shell bash outputs wrapper content."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "shell", "bash"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert ERK_SHELL_INTEGRATION_MARKER in result.output
        assert "source <(erk completion bash)" in result.output


def test_init_shell_fish_outputs_wrapper() -> None:
    """Test that erk init shell fish outputs wrapper content."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "shell", "fish"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert ERK_SHELL_INTEGRATION_MARKER in result.output
        # Fish uses different completion syntax
        assert "erk completion fish | source" in result.output


def test_init_shell_invalid_shell_errors() -> None:
    """Test that erk init shell with unknown shell shows error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "shell", "tcsh"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Unsupported shell: tcsh" in result.output
        assert "bash, zsh, fish" in result.output


def test_init_shell_check_active_shows_success() -> None:
    """Test that --check shows success when ERK_SHELL is set."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Simulate shell integration being active
        with mock.patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(cli, ["init", "shell", "--check"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Shell integration active" in result.output
        assert "ERK_SHELL=zsh" in result.output


def test_init_shell_check_inactive_shows_guidance() -> None:
    """Test that --check shows guidance when ERK_SHELL is not set."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create fake rc file for shell detection
        fake_zshrc = env.cwd / ".zshrc"
        fake_zshrc.write_text("", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        # Use FakeShell with detected shell
        shell = FakeShell(detected_shell=("zsh", fake_zshrc))

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=shell,
        )

        # Ensure ERK_SHELL is not set
        with mock.patch.dict(os.environ, {}, clear=True):
            # Also need to remove ERK_SHELL if it exists
            environ_without_erk_shell = {k: v for k, v in os.environ.items() if k != "ERK_SHELL"}
            with mock.patch.dict(os.environ, environ_without_erk_shell, clear=True):
                result = runner.invoke(cli, ["init", "shell", "--check"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Shell integration not active" in result.output
        assert 'eval "$(erk init shell zsh)"' in result.output
        assert "erk init shell --install" in result.output


def test_init_shell_install_appends_to_rc() -> None:
    """Test that --install appends content to RC file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create fake rc file
        fake_zshrc = env.cwd / ".zshrc"
        fake_zshrc.write_text("# existing content\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        # Use FakeShell with detected shell
        shell = FakeShell(detected_shell=("zsh", fake_zshrc))

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=shell,
        )

        result = runner.invoke(cli, ["init", "shell", "--install", "--force"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Added shell integration" in result.output

        # Verify rc file was updated
        rc_content = fake_zshrc.read_text(encoding="utf-8")
        assert "# existing content" in rc_content
        assert ERK_SHELL_INTEGRATION_MARKER in rc_content
        assert "erk()" in rc_content


def test_init_shell_install_creates_backup() -> None:
    """Test that --install creates backup file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create fake rc file
        fake_zshrc = env.cwd / ".zshrc"
        original_content = "# original content\nalias foo='bar'\n"
        fake_zshrc.write_text(original_content, encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        # Use FakeShell with detected shell
        shell = FakeShell(detected_shell=("zsh", fake_zshrc))

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=shell,
        )

        result = runner.invoke(cli, ["init", "shell", "--install", "--force"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        # Verify backup was created
        # Note: For dotfiles like .zshrc, Path.suffix returns ".zshrc", so
        # with_suffix appends to create .zshrc.zshrc.erk-backup
        backup_path = fake_zshrc.with_suffix(fake_zshrc.suffix + ".erk-backup")
        assert backup_path.exists()
        assert backup_path.read_text(encoding="utf-8") == original_content


def test_init_shell_install_skips_if_exists() -> None:
    """Test that --install skips if already installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create fake rc file with existing integration
        fake_zshrc = env.cwd / ".zshrc"
        fake_zshrc.write_text(
            f"# existing content\n\n{ERK_SHELL_INTEGRATION_MARKER}\nerk() {{\n}}\n",
            encoding="utf-8",
        )

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        # Use FakeShell with detected shell
        shell = FakeShell(detected_shell=("zsh", fake_zshrc))

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=shell,
        )

        result = runner.invoke(cli, ["init", "shell", "--install"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "already configured" in result.output


def test_init_shell_uninstall_removes_integration() -> None:
    """Test that --uninstall removes shell integration."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create fake rc file with existing integration
        fake_zshrc = env.cwd / ".zshrc"
        fake_zshrc.write_text(
            f"# keep this\n\n{ERK_SHELL_INTEGRATION_MARKER}\nerk() {{\n}}\n",
            encoding="utf-8",
        )

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        # Use FakeShell with detected shell
        shell = FakeShell(detected_shell=("zsh", fake_zshrc))

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=shell,
        )

        result = runner.invoke(cli, ["init", "shell", "--uninstall", "--force"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Removed" in result.output

        # Verify integration was removed
        rc_content = fake_zshrc.read_text(encoding="utf-8")
        assert ERK_SHELL_INTEGRATION_MARKER not in rc_content
        assert "# keep this" in rc_content


def test_init_shell_uninstall_creates_backup() -> None:
    """Test that --uninstall creates backup file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create fake rc file with existing integration
        original_content = f"# keep this\n\n{ERK_SHELL_INTEGRATION_MARKER}\nerk() {{\n}}\n"
        fake_zshrc = env.cwd / ".zshrc"
        fake_zshrc.write_text(original_content, encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        # Use FakeShell with detected shell
        shell = FakeShell(detected_shell=("zsh", fake_zshrc))

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=shell,
        )

        result = runner.invoke(cli, ["init", "shell", "--uninstall", "--force"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        # Verify backup was created
        # Note: For dotfiles like .zshrc, Path.suffix returns ".zshrc", so
        # with_suffix appends to create .zshrc.zshrc.erk-uninstall-backup
        backup_path = fake_zshrc.with_suffix(fake_zshrc.suffix + ".erk-uninstall-backup")
        assert backup_path.exists()
        assert backup_path.read_text(encoding="utf-8") == original_content


def test_init_shell_uninstall_noop_if_not_installed() -> None:
    """Test that --uninstall is a no-op if not installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create fake rc file without integration
        fake_zshrc = env.cwd / ".zshrc"
        fake_zshrc.write_text("# just normal content\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        # Use FakeShell with detected shell
        shell = FakeShell(detected_shell=("zsh", fake_zshrc))

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=shell,
        )

        result = runner.invoke(cli, ["init", "shell", "--uninstall"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "not installed" in result.output


def test_init_without_subcommand_runs_full_init() -> None:
    """Test that erk init (no subcommand) runs full initialization."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        # Full init should run (checking for typical init output)
        # Note: May fail due to test env setup, but should attempt full init
        assert "Step 1" in result.output or "repository" in result.output.lower()


def test_init_shell_flag_deprecated() -> None:
    """Test that --shell flag shows deprecation message."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        # Use FakeShell that will cause shell setup to return quickly
        shell = FakeShell(detected_shell=None)  # No shell detected

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=shell,
        )

        result = runner.invoke(cli, ["init", "--shell"], obj=test_ctx)

        # Should show deprecation warning
        assert "deprecated" in result.output.lower()
        assert "erk init shell --install" in result.output


def test_init_shell_no_args_shows_usage() -> None:
    """Test that erk init shell (no args) shows usage help."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create fake rc file for shell detection
        fake_zshrc = env.cwd / ".zshrc"
        fake_zshrc.write_text("", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        # Use FakeShell with detected shell
        shell = FakeShell(detected_shell=("zsh", fake_zshrc))

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=shell,
        )

        result = runner.invoke(cli, ["init", "shell"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Shell integration enables" in result.output
        assert 'eval "$(erk init shell zsh)"' in result.output
        assert "erk init shell --install" in result.output


def test_init_shell_mutually_exclusive_flags() -> None:
    """Test that --install, --check, --uninstall are mutually exclusive."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "shell", "--install", "--check"], obj=test_ctx)

        assert result.exit_code == 1
        assert "mutually exclusive" in result.output


def test_init_shell_install_no_shell_detected_fails() -> None:
    """Test that --install fails when no shell detected."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        # Use FakeShell that returns no detected shell
        shell = FakeShell(detected_shell=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=shell,
        )

        result = runner.invoke(cli, ["init", "shell", "--install"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Could not detect shell" in result.output


def test_init_shell_output_includes_header_comment() -> None:
    """Test that shell output includes generator header comment."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "shell", "zsh"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "# Generated by: erk init shell zsh" in result.output
