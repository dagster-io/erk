"""Tests for erk init capability add command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_capability_add_installs_capability() -> None:
    """Test that add command installs a capability."""
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

        # Verify capability is not installed initially
        assert not (env.cwd / "docs" / "learned").exists()

        result = runner.invoke(cli, ["init", "capability", "add", "learned-docs"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "learned-docs" in result.output
        assert "Created" in result.output or "already exists" in result.output

        # Verify capability was installed
        assert (env.cwd / "docs" / "learned").exists()


def test_capability_add_idempotent() -> None:
    """Test that adding an already installed capability is idempotent."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Pre-create the capability directory
        (env.cwd / "docs" / "learned").mkdir(parents=True)

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

        result = runner.invoke(cli, ["init", "capability", "add", "learned-docs"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "learned-docs" in result.output
        assert "already exists" in result.output


def test_capability_add_unknown_name_fails() -> None:
    """Test that add with unknown capability name fails with helpful error."""
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

        result = runner.invoke(cli, ["init", "capability", "add", "nonexistent"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Unknown capability: nonexistent" in result.output
        assert "Available capabilities:" in result.output


def test_capability_add_multiple() -> None:
    """Test that add command can install multiple capabilities at once."""
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

        # Currently only learned-docs is registered, so test with just that
        # but the command should handle multiple arguments
        result = runner.invoke(cli, ["init", "capability", "add", "learned-docs"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "learned-docs" in result.output


def test_capability_add_requires_repo() -> None:
    """Test that add command fails outside a git repository."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # FakeGit returns None for git_common_dir when not in a repo
        git_ops = FakeGit(git_common_dirs={})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "capability", "add", "learned-docs"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Not in a git repository" in result.output


def test_capability_add_requires_at_least_one_name() -> None:
    """Test that add command requires at least one capability name."""
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

        result = runner.invoke(cli, ["init", "capability", "add"], obj=test_ctx)

        # Click should fail because NAMES is required
        assert result.exit_code == 2
        assert "Missing argument" in result.output or "NAMES" in result.output
