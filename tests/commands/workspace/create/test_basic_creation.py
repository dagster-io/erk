"""Tests for basic worktree creation functionality."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_create_basic_worktree() -> None:
    """Test creating a basic worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create minimal config
        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Verify worktree creation from output
        assert "Created worktree" in result.output
        assert "test-feature" in result.output


def test_create_with_custom_branch_name() -> None:
    """Test creating a worktree with a custom branch name."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "feature", "--branch", "my-custom-branch"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        assert "my-custom-branch" in result.output


def test_create_requires_name_or_flag() -> None:
    """Test that create requires NAME or a flag."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Must provide NAME" in result.output


def test_create_with_branch_only_derives_name() -> None:
    """Test that --branch alone derives worktree name from branch.

    This enables: `erk wt create --branch license-update` to work,
    creating worktree and branch both named 'license-update'.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "--branch", "license-update"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "license-update" in result.output

        # Verify worktree was created with branch name
        expected_wt = repo_dir / "worktrees" / "license-update"
        assert (expected_wt, "license-update") in git_ops.added_worktrees
