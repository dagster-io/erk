"""Tests for submit command rollback on failure."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import submit_cmd
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.github.fake import FakeGitHub
from tests.commands.submit.conftest import create_plan
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def test_submit_push_failure_leaves_original_branch_intact(tmp_path: Path) -> None:
    """Test submit leaves user on original branch when push fails.

    When push_to_remote fails (e.g., network error), the user remains on
    their original branch. Since the submit path uses git plumbing
    (commit_files_to_branch) rather than checking out the plan branch,
    no branch restore is needed on failure.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    plan = create_plan("123", "Implement feature X")

    fake_plan_store, fake_github_issues = create_plan_store_with_plans({"123": plan})

    # Configure FakeGit to return an error on push_to_remote
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
        push_to_remote_error=PushError(message="Network error: Connection refused"),
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
    assert "Network error: Connection refused" in result.output

    # Verify no checkout of the plan branch occurred (plumbing commit, no checkout)
    plan_branch_checkouts = [
        branch for _, branch in fake_git.checked_out_branches if branch.startswith("P123-")
    ]
    assert len(plan_branch_checkouts) == 0

    # Verify workflow was NOT triggered (failure happened before workflow dispatch)
    assert len(fake_github.triggered_workflows) == 0

    # Verify no PR was created
    assert len(fake_github.created_prs) == 0
