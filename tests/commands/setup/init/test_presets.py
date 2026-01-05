"""Tests for preset auto-detection and explicit selection during init.

Mock Usage Policy:
------------------
This file uses minimal mocking for external boundaries:

1. Global config operations:
   - Uses FakeErkInstallation for dependency injection
   - No mocking required - proper abstraction via ConfigStore interface
   - Tests inject FakeErkInstallation with desired initial state
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_init_auto_preset_detects_dagster() -> None:
    """Test that auto preset detects dagster repo and uses dagster preset."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create pyproject.toml with dagster as the project name
        pyproject = env.cwd / "pyproject.toml"
        pyproject.write_text('[project]\nname = "dagster"\n', encoding="utf-8")

        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Config should be created in .erk/ directory (consolidated location)
        config_path = env.cwd / ".erk" / "config.toml"
        assert config_path.exists()


def test_init_auto_preset_uses_generic_fallback() -> None:
    """Test that auto preset falls back to generic for non-dagster repos."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create pyproject.toml with different project name
        pyproject = env.cwd / "pyproject.toml"
        pyproject.write_text('[project]\nname = "myproject"\n', encoding="utf-8")

        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Config should be created in .erk/ directory (consolidated location)
        config_path = env.cwd / ".erk" / "config.toml"
        assert config_path.exists()


def test_init_explicit_preset_dagster() -> None:
    """Test that explicit --preset dagster uses dagster preset."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(
            cli, ["init", "--preset", "dagster", "--no-interactive"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        # Config should be created in .erk/ directory (consolidated location)
        config_path = env.cwd / ".erk" / "config.toml"
        assert config_path.exists()


def test_init_explicit_preset_generic() -> None:
    """Test that explicit --preset generic uses generic preset."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(
            cli, ["init", "--preset", "generic", "--no-interactive"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        # Config should be created in .erk/ directory (consolidated location)
        config_path = env.cwd / ".erk" / "config.toml"
        assert config_path.exists()


def test_init_list_presets_displays_available() -> None:
    """Test that --list-presets displays available presets."""
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

        result = runner.invoke(cli, ["init", "--list-presets"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Available presets:" in result.output
        assert "dagster" in result.output
        assert "generic" in result.output


def test_init_invalid_preset_fails() -> None:
    """Test that invalid preset name fails with helpful error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--preset", "nonexistent"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid preset 'nonexistent'" in result.output
