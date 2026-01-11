"""Tests for erk init capability list command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_capability_list_shows_available_capabilities() -> None:
    """Test that list command shows all registered capabilities."""
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

        result = runner.invoke(cli, ["init", "capability", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Check section headers
        assert "Project capabilities:" in result.output
        assert "User capabilities:" in result.output
        # Check a project capability
        assert "learned-docs" in result.output
        assert "Autolearning documentation system" in result.output
        # Check a user capability
        assert "statusline" in result.output


def test_capability_list_works_without_repo() -> None:
    """Test that list command works outside a git repository."""
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

        result = runner.invoke(cli, ["init", "capability", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "learned-docs" in result.output
