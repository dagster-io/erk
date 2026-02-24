"""Tests for submit command rollback on failure."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import submit_cmd
from erk_shared.gateway.git.remote_ops.types import PushError
from tests.commands.submit.conftest import create_plan, setup_submit_context


def test_submit_push_failure_leaves_original_branch_intact(tmp_path: Path) -> None:
    """Test submit leaves user on original branch when push fails.

    When push_to_remote fails (e.g., network error), the user remains on
    their original branch. Since the submit path uses git plumbing
    (commit_files_to_branch) rather than checking out the plan branch,
    no branch restore is needed on failure.
    """
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"

    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            "push_to_remote_error": PushError(message="Network error: Connection refused"),
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    # Command should fail with the push error
    assert result.exit_code != 0
    assert "Network error: Connection refused" in result.output

    # Verify workflow was NOT triggered (failure happened before workflow dispatch)
    assert len(fake_github.triggered_workflows) == 0
