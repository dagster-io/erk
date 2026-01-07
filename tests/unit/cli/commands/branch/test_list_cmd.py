"""Tests for erk branch list command."""

from datetime import UTC, datetime, timedelta

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.builders import PullRequestInfoBuilder
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.output_helpers import strip_ansi


def test_branch_list_shows_branches_with_worktrees() -> None:
    """Test that branch list shows branches that have worktrees."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "feat-1", branch="feat-1", is_root=False),
                    WorktreeInfo(path=repo_dir / "feat-2", branch="feat-2", is_root=False),
                ],
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        graphite = FakeGraphite()
        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["branch", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)

        # Should show feature branches with worktrees (not trunk)
        assert "feat-1" in output
        assert "feat-2" in output
        # Trunk branch is filtered out
        assert "main" not in output


def test_branch_list_shows_branches_with_prs_only() -> None:
    """Test that branch list shows branches with open PRs even without worktrees."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ],
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Branch with open PR but no worktree
        pr = PullRequestInfoBuilder(123, "remote-branch").with_passing_checks().build()
        graphite = FakeGraphite(pr_info={"remote-branch": pr})
        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["branch", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)

        # Branch with PR but no worktree should be shown
        assert "remote-branch" in output
        assert "#123" in output
        # Worktree column should be "-" for this branch
        lines = output.strip().split("\n")
        for line in lines:
            if "remote-branch" in line:
                assert "-" in line  # No worktree


def test_branch_list_shows_branches_with_worktrees_and_prs() -> None:
    """Test that branch list shows branches with both worktrees and PRs."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "feat-1", branch="feat-1", is_root=False),
                ],
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Branch with worktree and PR
        pr = PullRequestInfoBuilder(456, "feat-1").with_passing_checks().build()
        graphite = FakeGraphite(pr_info={"feat-1": pr})
        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["branch", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)

        # Should show branch with both worktree name and PR info
        assert "feat-1" in output
        assert "#456" in output
        assert "OPEN" in output


def test_branch_list_excludes_closed_prs_without_worktrees() -> None:
    """Test that branches with closed PRs but no worktrees are not shown."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ],
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Branch with closed PR and no worktree
        pr = PullRequestInfoBuilder(789, "old-branch").as_closed().build()
        graphite = FakeGraphite(pr_info={"old-branch": pr})
        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["branch", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)

        # Closed PR without worktree should NOT be shown
        assert "old-branch" not in output


def test_branch_list_shows_empty_table_when_no_active_branches() -> None:
    """Test that branch list shows empty table when no active branches."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ],
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        graphite = FakeGraphite()
        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["branch", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Should complete successfully with just headers (trunk filtered out)
        output = strip_ansi(result.output)
        assert "branch" in output  # Header is shown


def test_branch_list_ls_alias() -> None:
    """Test that 'erk branch ls' works as alias for 'erk branch list'."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "feat-1", branch="feat-1", is_root=False),
                ],
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        graphite = FakeGraphite()
        test_ctx = env.build_context(git=git, graphite=graphite)

        # Use 'ls' alias
        result = runner.invoke(cli, ["branch", "ls"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)
        assert "feat-1" in output


def test_branch_list_br_group_alias() -> None:
    """Test that 'erk br ls' works as shorthand for 'erk branch ls'."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "feat-1", branch="feat-1", is_root=False),
                ],
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        graphite = FakeGraphite()
        test_ctx = env.build_context(git=git, graphite=graphite)

        # Use 'br ls' shorthand
        result = runner.invoke(cli, ["br", "ls"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)
        assert "feat-1" in output


def test_branch_list_shows_root_worktree_as_root() -> None:
    """Test that root worktree is labeled 'root' when branch is on root worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        # Root worktree has a feature branch checked out (not main)
        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="feature-on-root", is_root=True),
                    WorktreeInfo(path=repo_dir / "other", branch="other-feat", is_root=False),
                ],
            },
            current_branches={env.cwd: "feature-on-root"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        graphite = FakeGraphite()
        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["branch", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)

        # Root worktree branch should show "root" as worktree name
        assert "feature-on-root" in output
        assert "root" in output


def test_branch_list_shows_pr_status_emoji() -> None:
    """Test that PR status emojis are shown correctly."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "passing", branch="passing", is_root=False),
                    WorktreeInfo(path=repo_dir / "failing", branch="failing", is_root=False),
                    WorktreeInfo(path=repo_dir / "draft", branch="draft", is_root=False),
                ],
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # PRs with different statuses
        passing_pr = PullRequestInfoBuilder(1, "passing").with_passing_checks().build()
        failing_pr = PullRequestInfoBuilder(2, "failing").with_failing_checks().build()
        draft_pr = PullRequestInfoBuilder(3, "draft").as_draft().build()

        graphite = FakeGraphite(
            pr_info={"passing": passing_pr, "failing": failing_pr, "draft": draft_pr}
        )
        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["branch", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = result.output  # Keep emojis for this test

        # Should show different emojis for different statuses
        assert "✅" in output  # Passing
        assert "❌" in output  # Failing
        assert "🚧" in output  # Draft


def test_branch_list_sorted_alphabetically() -> None:
    """Test that branches are sorted alphabetically."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "zebra", branch="zebra", is_root=False),
                    WorktreeInfo(path=repo_dir / "apple", branch="apple", is_root=False),
                    WorktreeInfo(path=repo_dir / "middle", branch="middle", is_root=False),
                ],
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        graphite = FakeGraphite()
        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["branch", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)
        lines = [line for line in output.strip().split("\n") if line.strip()]

        # Find lines with branch names (skip header)
        branch_names = ["apple", "middle", "zebra"]
        branch_lines = [line for line in lines if any(b in line for b in branch_names)]

        # Extract order of appearance
        found_order = []
        for line in branch_lines:
            if "apple" in line:
                found_order.append("apple")
            elif "middle" in line:
                found_order.append("middle")
            elif "zebra" in line:
                found_order.append("zebra")

        # Should be alphabetically sorted
        expected = ["apple", "middle", "zebra"]
        assert found_order == expected, f"Expected alphabetical order, got {found_order}"


def test_branch_list_shows_last_commit_column() -> None:
    """Test that branch list shows the 'last' column with relative timestamps."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        # Create timestamps for branches
        two_days_ago = datetime.now(UTC) - timedelta(days=2)
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "feat-1", branch="feat-1", is_root=False),
                    WorktreeInfo(path=repo_dir / "feat-2", branch="feat-2", is_root=False),
                ],
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            branch_last_commit_times={
                "feat-1": two_days_ago.isoformat(),
                "feat-2": one_hour_ago.isoformat(),
            },
        )

        graphite = FakeGraphite()
        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["branch", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)

        # Should show 'last' column header
        assert "last" in output

        # Should show relative timestamps for feature branches
        assert "2d ago" in output
        assert "1h ago" in output


def test_branch_list_shows_dash_for_no_unique_commits() -> None:
    """Test that branches with no unique commits show '-' in last column."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "no-commits", branch="no-commits", is_root=False),
                ],
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            branch_last_commit_times={},  # No last commit times
        )

        graphite = FakeGraphite()
        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["branch", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)

        # Branch should be shown
        assert "no-commits" in output
        # And the row should have dashes (for last column and other empty columns)
        lines = output.strip().split("\n")
        for line in lines:
            if "no-commits" in line:
                # The line should contain "-" entries (worktree might also be shown)
                assert "-" in line
