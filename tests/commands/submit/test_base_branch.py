"""Tests for custom base branch handling in submit."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import submit_cmd
from tests.commands.submit.conftest import create_plan, setup_submit_context


def test_submit_with_custom_base_branch(tmp_path: Path) -> None:
    """Test submit passes custom base branch in workflow when --base is specified."""
    plan = create_plan("123", "Implement feature X")

    repo_root = tmp_path / "repo"
    # Custom feature branch exists on remote - add to remote_branch_refs
    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        {"123": plan},
        remote_branch_refs=[
            "origin/main",
            "origin/feature/parent-branch",
            "origin/plnd/123-implement-feature-x",
        ],
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "--base", "feature/parent-branch"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "issue(s) submitted successfully!" in result.output

    # Verify workflow was triggered with custom base_branch in inputs
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert inputs["base_branch"] == "feature/parent-branch"

    # Note: In planned_pr backend, PR already exists with correct base.
    # No PR creation or branch creation happens in submit.


def test_submit_with_invalid_base_branch(tmp_path: Path) -> None:
    """Test submit fails early when --base branch doesn't exist on remote (LBYL)."""
    plan = create_plan("123", "Implement feature X")

    # "nonexistent-branch" does NOT exist on remote
    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        {"123": plan},
        remote_branch_refs=[],  # Empty - no remote branches
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "--base", "nonexistent-branch"], obj=ctx)

    # Should fail early with error (LBYL)
    assert result.exit_code == 1
    assert "Error: Base branch 'nonexistent-branch' does not exist on remote" in result.output

    # Verify workflow was NOT triggered (failure happened before workflow dispatch)
    assert len(fake_github.triggered_workflows) == 0


def test_submit_passes_base_branch_in_workflow(tmp_path: Path) -> None:
    """Test submit passes base_branch in workflow inputs for stacked branch support.

    The base_branch is used by the remote worker to rebase onto the correct parent
    branch (not always trunk) when resolving merge conflicts.
    """
    plan = create_plan("456", "Implement stacked feature")

    repo_root = tmp_path / "repo"
    # Parent branch exists on remote
    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        {"456": plan},
        git_kwargs={
            "current_branches": {repo_root: "feature-parent"},
            "trunk_branches": {repo_root: "master"},
        },
        remote_branch_refs=[
            "origin/feature-parent",
            "origin/plnd/456-implement-stacked-feature",
        ],
    )

    runner = CliRunner()
    # Submit from feature-parent (current branch is used as base by default)
    result = runner.invoke(submit_cmd, ["456"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify workflow was triggered with base_branch in inputs
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert workflow == "plan-implement.yml"
    assert inputs["plan_id"] == "456"
    # CRITICAL: base_branch must be passed to workflow for stacked PR support
    assert "base_branch" in inputs
    assert inputs["base_branch"] == "feature-parent"


def test_submit_custom_base_passes_in_workflow(tmp_path: Path) -> None:
    """Test submit with --base passes custom base_branch in workflow inputs."""
    plan = create_plan("789", "Implement child feature")

    repo_root = tmp_path / "repo"
    # Custom parent branch exists on remote
    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        {"789": plan},
        remote_branch_refs=[
            "origin/main",
            "origin/feature-parent",
            "origin/plnd/789-implement-child-feature",
        ],
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["789", "--base", "feature-parent"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify workflow was triggered with custom base_branch
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    # CRITICAL: Custom base_branch must be passed for stacked PR rebase support
    assert inputs["base_branch"] == "feature-parent"
