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

    # Verify PR was created with trunk as base (not the placeholder branch)
    assert len(fake_github.created_prs) == 1
    _, _, _, base, _ = fake_github.created_prs[0]
    assert base == "master"  # Should be trunk, NOT __erk-slot-02-br-stub__

    # Verify branch was created from trunk
    assert len(fake_git.created_branches) == 1
    _, _, created_base = fake_git.created_branches[0]
    assert created_base == "origin/master"


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

    # Verify PR was created with explicit base (not trunk, not placeholder)
    assert len(fake_github.created_prs) == 1
    _, _, _, base, _ = fake_github.created_prs[0]
    assert base == "feature/custom-base"


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

    # Verify PR was created with current branch as base
    assert len(fake_github.created_prs) == 1
    _, _, _, base, _ = fake_github.created_prs[0]
    assert base == "feature/parent"  # Current branch, NOT trunk


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

    # Verify PR was created with trunk as base (not the unpushed branch)
    assert len(fake_github.created_prs) == 1
    _, _, _, base, _ = fake_github.created_prs[0]
    assert base == "master"  # Should be trunk, NOT feature/local-only

    # Verify branch was created from trunk
    assert len(fake_git.created_branches) == 1
    _, _, created_base = fake_git.created_branches[0]
    assert created_base == "origin/master"
