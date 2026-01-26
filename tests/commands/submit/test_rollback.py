"""Tests for submit command rollback on failure."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import submit_cmd
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from tests.commands.submit.conftest import create_plan
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def test_submit_rollback_on_push_failure(tmp_path: Path) -> None:
    """Test submit restores original branch when push fails.

    When push_to_remote fails (e.g., network error), the user should be
    restored to their original branch instead of being stranded on an
    unpushed local branch.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    plan = create_plan("123", "Implement feature X")

    fake_plan_store, fake_github_issues = create_plan_store_with_plans({"123": plan})

    # Configure FakeGit to raise an exception on push_to_remote
    push_error = RuntimeError("Network error: Connection refused")
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
        push_to_remote_raises=push_error,
    )
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    # Command should fail with the push error
    assert result.exit_code != 0
    assert "Operation failed, restoring original branch" in result.output

    # Verify rollback: user should be restored to original branch "main"
    # Check that checkout_branch was called with "main" after the failed push
    # The sequence should be: checkout feature branch, then checkout main (rollback)
    assert len(fake_git.checked_out_branches) >= 2

    # Last checkout should be the rollback to original branch
    last_checkout = fake_git.checked_out_branches[-1]
    assert last_checkout == (repo_root, "main")

    # Verify workflow was NOT triggered (failure happened before workflow dispatch)
    assert len(fake_github.triggered_workflows) == 0

    # Verify no PR was created
    assert len(fake_github.created_prs) == 0
