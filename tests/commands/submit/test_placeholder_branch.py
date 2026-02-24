"""Tests for placeholder branch handling in submit."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import submit_cmd
from tests.commands.submit.conftest import create_plan, setup_submit_context


def test_submit_from_placeholder_branch_uses_trunk(tmp_path: Path) -> None:
    """Test submit uses trunk as base when on a placeholder branch (no --base)."""
    plan = create_plan("123", "Implement feature X")

    # setup_submit_context creates repo_root, get path for git_kwargs
    repo_root = tmp_path / "repo"

    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        plans={"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "__erk-slot-02-br-stub__"},
            "trunk_branches": {repo_root: "master"},
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "issue(s) submitted successfully!" in result.output

    # Verify workflow was triggered with trunk as base branch (not placeholder)
    assert len(fake_github.triggered_workflows) == 1
    _workflow, inputs = fake_github.triggered_workflows[0]
    assert inputs["base_branch"] == "master"


def test_submit_from_placeholder_branch_with_explicit_base(tmp_path: Path) -> None:
    """Test --base overrides placeholder detection (explicit base takes precedence)."""
    plan = create_plan("123", "Implement feature X")

    # setup_submit_context creates repo_root, get path for git_kwargs
    repo_root = tmp_path / "repo"

    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        plans={"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "__erk-slot-02-br-stub__"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/feature/custom-base"]},
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "--base", "feature/custom-base"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify workflow was triggered with explicit base (not trunk, not placeholder)
    assert len(fake_github.triggered_workflows) == 1
    _workflow, inputs = fake_github.triggered_workflows[0]
    assert inputs["base_branch"] == "feature/custom-base"


def test_submit_from_non_placeholder_branch_uses_current(tmp_path: Path) -> None:
    """Test submit uses current branch as base for non-placeholder branches."""
    plan = create_plan("123", "Implement feature X")

    # setup_submit_context creates repo_root, get path for git_kwargs
    repo_root = tmp_path / "repo"

    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        plans={"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "feature/parent"},
            "trunk_branches": {repo_root: "master"},
            "remote_branches": {repo_root: ["origin/feature/parent"]},
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify workflow was triggered with current branch as base
    assert len(fake_github.triggered_workflows) == 1
    _workflow, inputs = fake_github.triggered_workflows[0]
    assert inputs["base_branch"] == "feature/parent"


def test_submit_from_unpushed_branch_uses_trunk(tmp_path: Path) -> None:
    """Test submit uses trunk as base when on a non-placeholder branch not pushed to remote."""
    plan = create_plan("123", "Implement feature X")

    repo_root = tmp_path / "repo"

    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        plans={"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "feature/local-only"},
            "trunk_branches": {repo_root: "master"},
            # Note: remote_branches does NOT include origin/feature/local-only
            "remote_branches": {repo_root: []},
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "issue(s) submitted successfully!" in result.output

    # Verify workflow was triggered with trunk as base (not the unpushed branch)
    assert len(fake_github.triggered_workflows) == 1
    _workflow, inputs = fake_github.triggered_workflows[0]
    assert inputs["base_branch"] == "master"
