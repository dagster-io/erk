"""Tests for remote branch validation in worktree creation."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_create_fails_when_branch_exists_on_remote() -> None:
    """Test that create fails if branch name already exists on origin."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            remote_branches={env.cwd: ["origin/main", "origin/existing-feature"]},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "existing-feature"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already exists on remote" in result.output
        assert "origin" in result.output


def test_create_succeeds_when_branch_not_on_remote() -> None:
    """Test that create succeeds if branch name doesn't exist on origin."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            remote_branches={env.cwd: ["origin/main"]},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "new-feature"], obj=test_ctx)

        assert result.exit_code == 0
        assert "new-feature" in result.output


def test_create_with_skip_remote_check_flag() -> None:
    """Test that --skip-remote-check bypasses remote validation."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            remote_branches={env.cwd: ["origin/main", "origin/existing-feature"]},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli,
            ["wt", "create", "existing-feature", "--skip-remote-check"],
            obj=test_ctx,
        )

        assert result.exit_code == 0
        assert "existing-feature" in result.output


def test_create_proceeds_with_warning_when_remote_check_fails() -> None:
    """Test that create proceeds with warning if remote check fails."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Create FakeGit that raises exception on list_remote_branches
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # Override list_remote_branches to raise exception
        def failing_list_remote_branches(repo_root):
            raise Exception("Network error")

        git_ops.list_remote_branches = failing_list_remote_branches

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "new-feature"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Warning:" in result.output
        assert "Could not check remote branches" in result.output
        assert "new-feature" in result.output
