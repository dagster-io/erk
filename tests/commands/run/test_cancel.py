"""CLI tests for erk run cancel command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.run.cancel_cmd import cancel_run
from erk_shared.gateway.git.abc import WorktreeInfo
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.tests.context import create_test_context


def test_cancel_run_success(tmp_path: Path) -> None:
    """Test cancelling a workflow run records the cancellation."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    github_ops = FakeLocalGitHub()
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()
    result = runner.invoke(cancel_run, ["12345"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "Cancelled" in result.output
    assert "12345" in result.output
    assert github_ops.cancelled_run_ids == ["12345"]
