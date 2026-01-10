"""Tests for erk init capability check command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_capability_check_shows_not_installed() -> None:
    """Test that check shows capability as not installed when directory doesn't exist."""
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

        result = runner.invoke(cli, ["init", "capability", "check"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should show learned-docs as not installed (○)
        assert "learned-docs" in result.output


def test_capability_check_shows_installed() -> None:
    """Test that check shows capability as installed when directory exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create docs/learned/ to make capability appear installed
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

        result = runner.invoke(cli, ["init", "capability", "check"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "learned-docs" in result.output


def test_capability_check_specific_name() -> None:
    """Test that check with a specific name shows only that capability."""
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

        result = runner.invoke(cli, ["init", "capability", "check", "learned-docs"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "learned-docs" in result.output
        assert "Autolearning documentation system" in result.output


def test_capability_check_unknown_name_fails() -> None:
    """Test that check with unknown capability name fails with helpful error."""
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

        result = runner.invoke(cli, ["init", "capability", "check", "nonexistent"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Unknown capability: nonexistent" in result.output
        assert "Available capabilities:" in result.output


def test_capability_check_outside_repo_shows_unknown_for_project_caps() -> None:
    """Test that check command outside git repo shows '?' for project capabilities."""
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

        result = runner.invoke(cli, ["init", "capability", "check"], obj=test_ctx)

        # Should succeed because user-level capabilities can still be checked
        assert result.exit_code == 0, result.output
        # Project capabilities should show as "?" (unknown status)
        assert "learned-docs" in result.output
        assert "[project]" in result.output
        # User capabilities should show normally
        assert "statusline" in result.output
        assert "[user]" in result.output


def test_capability_check_specific_project_cap_requires_repo() -> None:
    """Test that checking a specific project-level capability fails outside git repo."""
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

        result = runner.invoke(cli, ["init", "capability", "check", "learned-docs"], obj=test_ctx)

        assert result.exit_code == 1
        assert "project-level capability" in result.output
        assert "git repository" in result.output


def test_capability_check_shows_artifacts_when_installed() -> None:
    """Test that check with name shows artifact details when installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create docs/learned/ with README to make capability appear installed
        (env.cwd / "docs" / "learned").mkdir(parents=True)
        (env.cwd / "docs" / "learned" / "README.md").write_text("# Test", encoding="utf-8")

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

        result = runner.invoke(cli, ["init", "capability", "check", "learned-docs"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should show installation check description
        assert "Checks for:" in result.output
        assert "docs/learned" in result.output
        # Should show artifacts section
        assert "Artifacts:" in result.output
        assert "docs/learned/" in result.output
        assert "README.md" in result.output
        assert "directory" in result.output
        assert "file" in result.output


def test_capability_check_shows_artifacts_when_not_installed() -> None:
    """Test that check with name shows artifact details when not installed."""
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

        result = runner.invoke(cli, ["init", "capability", "check", "learned-docs"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should show installation check description
        assert "Checks for:" in result.output
        # Should show artifacts with helpful message
        assert "would be created by" in result.output
        assert "erk init capability add learned-docs" in result.output
        assert "docs/learned/" in result.output
        assert "README.md" in result.output


def test_capability_check_shows_installation_check_description() -> None:
    """Test that check with name shows what the installation check verifies."""
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

        result = runner.invoke(cli, ["init", "capability", "check", "learned-docs"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should show the installation check description
        assert "Checks for: docs/learned/ directory exists" in result.output
