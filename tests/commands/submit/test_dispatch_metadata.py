"""Tests for workflow dispatch metadata tracking."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import submit_cmd
from erk_shared.github.fake import FakeGitHub
from tests.commands.submit.conftest import create_plan, setup_submit_context


def test_submit_updates_dispatch_info_in_issue(tmp_path: Path) -> None:
    """Test submit updates issue body with dispatch info after triggering workflow."""
    plan = create_plan("123", "Implement feature X")
    ctx, _, _, fake_github_issues, _, repo_root = setup_submit_context(tmp_path, {"123": plan})

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "Dispatch metadata written to issue" in result.output

    # Verify issue body was updated with dispatch info
    updated_issue = fake_github_issues.get_issue(repo_root, 123)
    assert "last_dispatched_run_id: '1234567890'" in updated_issue.body
    assert "last_dispatched_node_id: WFR_fake_node_id_1234567890" in updated_issue.body
    assert "last_dispatched_at:" in updated_issue.body


def test_submit_warns_when_node_id_not_available(tmp_path: Path) -> None:
    """Test submit warns but continues when workflow run node_id cannot be fetched."""
    plan = create_plan("123", "Implement feature X")

    # Create a custom FakeGitHub that returns None for node_id lookup
    class FakeGitHubNoNodeId(FakeGitHub):
        def get_workflow_run_node_id(self, repo_root: Path, run_id: str) -> None:
            # Return None to simulate failure to fetch node_id
            return None

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    from erk.core.context import context_for_test
    from erk.core.repo_discovery import RepoContext
    from erk_shared.git.fake import FakeGit
    from tests.test_utils.plan_helpers import create_plan_store_with_plans

    fake_plan_store, fake_github_issues = create_plan_store_with_plans({"123": plan})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    fake_github = FakeGitHubNoNodeId()

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

    # Should succeed but warn about missing node_id
    assert result.exit_code == 0, result.output
    assert "Could not fetch workflow run node_id" in result.output
    # Workflow should still be triggered successfully
    assert "1 issue(s) submitted successfully!" in result.output
