"""Tests for basic wt list command output."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.integrations.graphite.fake import FakeGraphite
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.output_helpers import strip_ansi


def test_list_outputs_names_not_paths() -> None:
    """Test that list outputs worktree names, not full paths."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create worktrees in the location determined by global config
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name

        # Build fake git ops with worktree info
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=repo_dir / "foo", branch="foo"),
                    WorktreeInfo(path=repo_dir / "bar", branch="feature/bar"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(pr_info={}),
            show_pr_info=False,  # Don't require PR info for this test
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier comparison
        output = strip_ansi(result.output)

        # Should show worktree names
        assert "root" in output
        assert "foo" in output
        assert "bar" in output

        # Should show branch info
        assert "(main)" in output
        assert "(=)" in output  # foo == foo
        assert "(feature/bar)" in output

        # New format has columns: worktree, branch, pr, sync, impl
        # Check for column headers
        assert "worktree" in output
        assert "branch" in output
        assert "pr" in output
        assert "sync" in output
        assert "impl" in output


def test_list_shows_equal_for_matching_branch() -> None:
    """Test that (=) is shown when worktree name matches branch name."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=repo_dir / "feature-branch", branch="feature-branch"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(pr_info={}),
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)
        # When worktree name matches branch name, show (=)
        assert "(=)" in output


def test_list_shows_cwd_indicator() -> None:
    """Test that current working directory is indicated with (cwd)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(pr_info={}),
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)
        # Current working directory indicator
        assert "(cwd)" in output
