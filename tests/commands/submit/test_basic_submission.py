"""Tests for basic submit command functionality."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import submit_cmd
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.commands.submit.conftest import create_plan, setup_submit_context


def test_submit_planned_pr_checkouts_fetches_and_pushes(tmp_path: Path) -> None:
    """Test submit fetches existing PR branch, adds impl-context, and pushes."""
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    ctx, fake_git, fake_github, _, _, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "issue(s) submitted successfully!" in result.output
    assert "Workflow:" in result.output

    # Branch name is plnd/123-implement-feature-x (from PRDetails)
    expected_branch = "plnd/123-implement-feature-x"

    # Verify branch was fetched from remote
    assert len(fake_git.fetched_branches) >= 1
    fetched = [f for f in fake_git.fetched_branches if f[1] == expected_branch]
    assert len(fetched) == 1
    assert fetched[0] == ("origin", expected_branch)

    # Verify branch was checked out
    assert expected_branch in [b[1] for b in fake_git.checked_out_branches]

    # Verify branch was pushed (with impl-context commit)
    assert len(fake_git.pushed_branches) >= 1
    pushed = [p for p in fake_git.pushed_branches if p[1] == expected_branch]
    assert len(pushed) == 1
    remote, branch, set_upstream, force = pushed[0]
    assert remote == "origin"
    assert set_upstream is False  # Branch already exists on remote
    assert force is False

    # Verify NO PR was created (PR already exists)
    assert len(fake_github.created_prs) == 0

    # Verify workflow was triggered with plan_backend="planned_pr"
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert workflow == "plan-implement.yml"
    assert inputs["plan_id"] == "123"
    assert inputs["plan_backend"] == "planned_pr"


def test_submit_planned_pr_does_not_track_existing_branch(tmp_path: Path) -> None:
    """Test submit does NOT track branch with Graphite (branch already exists).

    For planned-PR workflow, branches are created outside of submit and already
    exist on remote. Submit just checks them out - no Graphite tracking is needed
    since the branch already exists in Graphite's metadata.
    """
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    ctx, fake_git, fake_github, _, fake_graphite, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
        },
        graphite_kwargs={
            # main must be tracked for stacking to work
            "branches": {
                "main": BranchMetadata.trunk("main"),
            },
        },
        use_graphite=True,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify branch was NOT tracked with Graphite (it already exists)
    # Planned-PR branches are created elsewhere and already tracked
    assert len(fake_graphite.track_branch_calls) == 0


def test_submit_displays_workflow_run_url(tmp_path: Path) -> None:
    """Test submit displays workflow run URL from trigger_workflow response."""
    plan = create_plan("123", "Add workflow run URL to erk submit output")
    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(tmp_path, {"123": plan})

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "issue(s) submitted successfully!" in result.output
    # Verify workflow run URL is displayed (uses run_id returned by trigger_workflow)
    expected_url = "https://github.com/test-owner/test-repo/actions/runs/1234567890"
    assert expected_url in result.output


def test_submit_single_pr_still_works(tmp_path: Path) -> None:
    """Test backwards compatibility: single PR argument still works."""
    plan = create_plan("123", "Implement feature X")
    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(tmp_path, {"123": plan})

    runner = CliRunner()
    # Single argument - backwards compatibility
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "1 issue(s) submitted successfully!" in result.output
    assert "Workflow:" in result.output

    # Verify branch was fetched and checked out (not created)
    assert len(fake_git.fetched_branches) >= 1
    assert len(fake_git.checked_out_branches) >= 1

    # Verify workflow was triggered
    assert len(fake_github.triggered_workflows) == 1
