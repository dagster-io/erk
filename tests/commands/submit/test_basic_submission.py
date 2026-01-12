"""Tests for basic submit command functionality."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import submit_cmd
from tests.commands.submit.conftest import create_plan, setup_submit_context


def test_submit_creates_branch_and_draft_pr(tmp_path: Path) -> None:
    """Test submit creates linked branch, pushes, creates draft PR, triggers workflow."""
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    ctx, fake_git, fake_github, _, _, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/main"]},
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "issue(s) submitted successfully!" in result.output
    assert "Workflow:" in result.output

    # Branch name is sanitize_worktree_name(...) + timestamp suffix "-01-15-1430"
    expected_branch = "P123-implement-feature-x-01-15-1430"

    # Verify branch was created via git (from origin/<current_branch>)
    # Note: submit defaults to current branch as base, not trunk_branch
    assert len(fake_git.created_branches) == 1
    created_repo, created_branch, created_base = fake_git.created_branches[0]
    assert created_repo == repo_root
    assert created_branch == expected_branch
    assert created_base == "origin/main"  # Uses current branch as base

    # Verify branch was pushed
    assert len(fake_git.pushed_branches) == 1
    remote, branch, set_upstream, force = fake_git.pushed_branches[0]
    assert remote == "origin"
    assert branch == expected_branch
    assert set_upstream is True
    assert force is False

    # Verify draft PR was created
    assert len(fake_github.created_prs) == 1
    branch_name, title, body, base, draft = fake_github.created_prs[0]
    assert branch_name == expected_branch
    assert title == "Implement feature X"
    assert draft is True
    # PR body contains plan reference
    assert "**Plan:** #123" in body

    # Verify workflow was triggered
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert workflow == "erk-impl.yml"
    assert inputs["issue_number"] == "123"

    # Verify local branch was cleaned up
    assert len(fake_git._deleted_branches) == 1
    assert expected_branch in fake_git._deleted_branches


def test_submit_tracks_branch_with_graphite(tmp_path: Path) -> None:
    """Test submit tracks the created branch with Graphite for proper PR stacking.

    When branches are created via submit, they must be tracked with Graphite
    so that `erk land` can find child PRs and update their base branches before
    merging. Without tracking, child PRs get auto-closed by GitHub when their
    base branch is deleted.
    """
    plan = create_plan("123", "Implement feature X")
    repo_root = tmp_path / "repo"
    ctx, fake_git, fake_github, _, fake_graphite, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/main"]},
        },
        use_graphite=True,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Branch name is sanitize_worktree_name(...) + timestamp suffix "-01-15-1430"
    expected_branch = "P123-implement-feature-x-01-15-1430"

    # Verify branch was tracked with Graphite (critical for child PR detection)
    assert len(fake_graphite.track_branch_calls) == 1
    tracked_repo, tracked_branch, parent_branch = fake_graphite.track_branch_calls[0]
    assert tracked_repo == repo_root
    assert tracked_branch == expected_branch
    assert parent_branch == "main"  # Base branch without origin/ prefix


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


def test_submit_single_issue_still_works(tmp_path: Path) -> None:
    """Test backwards compatibility: single issue argument still works."""
    plan = create_plan("123", "Implement feature X")
    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(tmp_path, {"123": plan})

    runner = CliRunner()
    # Single argument - backwards compatibility
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "1 issue(s) submitted successfully!" in result.output
    assert "Workflow:" in result.output

    # Verify branch was created via git
    assert len(fake_git.created_branches) == 1

    # Verify workflow was triggered
    assert len(fake_github.triggered_workflows) == 1
