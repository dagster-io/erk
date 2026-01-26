"""Tests for learn plan handling in submit."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import get_learn_plan_parent_branch, is_issue_learn_plan, submit_cmd
from erk_shared.gateway.github.metadata.core import render_metadata_block
from erk_shared.gateway.github.metadata.types import MetadataBlock
from erk_shared.gateway.gt.operations.finalize import ERK_SKIP_LEARN_LABEL
from tests.commands.submit.conftest import (
    create_plan,
    make_learn_plan_body,
    make_plan_body,
    setup_submit_context,
)


def test_is_issue_learn_plan_returns_true_when_erk_learn_label_present() -> None:
    """Test is_issue_learn_plan returns True when erk-learn label is present."""
    labels = ["erk-plan", "erk-learn"]
    result = is_issue_learn_plan(labels)
    assert result is True


def test_is_issue_learn_plan_returns_false_when_erk_learn_label_absent() -> None:
    """Test is_issue_learn_plan returns False when erk-learn label is not present."""
    labels = ["erk-plan", "bug"]
    result = is_issue_learn_plan(labels)
    assert result is False


def test_is_issue_learn_plan_returns_false_for_empty_labels() -> None:
    """Test is_issue_learn_plan returns False for empty labels list."""
    labels: list[str] = []
    result = is_issue_learn_plan(labels)
    assert result is False


def test_submit_learn_plan_adds_skip_learn_label(tmp_path: Path) -> None:
    """Test submit adds erk-skip-learn label to PR for learn plans."""
    # Plan with erk-learn label
    learn_body = make_learn_plan_body()
    plan = create_plan(
        "123",
        "Extract documentation from session X",
        body=learn_body,
        labels=["erk-plan", "erk-learn"],
    )
    ctx, _, fake_github, _, _, _ = setup_submit_context(tmp_path, {"123": plan})

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify erk-skip-learn label was added to PR
    assert len(fake_github.added_labels) == 1
    pr_number, label = fake_github.added_labels[0]
    assert pr_number == 999  # FakeGitHub returns 999 for created PRs
    assert label == ERK_SKIP_LEARN_LABEL

    # Verify PR body was updated (checkout command, no learn marker)
    assert len(fake_github.updated_pr_bodies) == 1
    _, updated_body = fake_github.updated_pr_bodies[0]
    assert "erk pr checkout" in updated_body


def test_submit_standard_plan_does_not_add_skip_learn_label(tmp_path: Path) -> None:
    """Test submit does NOT add erk-skip-learn label for standard plans."""
    # Standard plan (no erk-learn label)
    standard_body = make_plan_body()
    plan = create_plan("456", "Implement feature Y", body=standard_body, labels=["erk-plan"])
    ctx, _, fake_github, _, _, _ = setup_submit_context(tmp_path, {"456": plan})

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["456"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify NO label was added (standard plan, not learn)
    assert len(fake_github.added_labels) == 0

    # Verify PR body was updated (checkout command only)
    assert len(fake_github.updated_pr_bodies) == 1
    _, updated_body = fake_github.updated_pr_bodies[0]
    assert "erk pr checkout" in updated_body


def _make_learn_plan_body_with_parent(learned_from_issue: int) -> str:
    """Create a learn plan issue body that links to a parent issue."""
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "test-user",
        "learned_from_issue": learned_from_issue,
    }
    header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))
    return f"{header_block}\n\n# Learn Plan\n\nDocumentation learning..."


def _make_parent_plan_body_with_branch(branch_name: str) -> str:
    """Create a parent plan issue body with a branch name."""
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "test-user",
        "branch_name": branch_name,
    }
    header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))
    return f"{header_block}\n\n# Plan\n\nImplementation details..."


def test_get_learn_plan_parent_branch_returns_parent_branch(tmp_path: Path) -> None:
    """Test get_learn_plan_parent_branch returns parent's branch_name."""
    # Parent plan with branch_name
    parent_body = _make_parent_plan_body_with_branch("P5637-add-github-01-23-0433")
    parent_plan = create_plan(
        "5637", "Add generic GitHub API", body=parent_body, labels=["erk-plan"]
    )

    # Learn plan referencing parent
    learn_body = _make_learn_plan_body_with_parent(learned_from_issue=5637)
    learn_plan = create_plan(
        "5652", "Extract docs from session", body=learn_body, labels=["erk-plan", "erk-learn"]
    )

    ctx, _, _, _, _, repo_root = setup_submit_context(
        tmp_path, {"5637": parent_plan, "5652": learn_plan}
    )

    result = get_learn_plan_parent_branch(ctx, repo_root, learn_body)

    assert result == "P5637-add-github-01-23-0433"


def test_get_learn_plan_parent_branch_returns_none_without_learned_from(tmp_path: Path) -> None:
    """Test get_learn_plan_parent_branch returns None when learned_from_issue is missing."""
    # Learn plan without learned_from_issue
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "test-user",
    }
    header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))
    learn_body = f"{header_block}\n\n# Learn Plan\n\nDocumentation..."

    learn_plan = create_plan(
        "5652", "Extract docs", body=learn_body, labels=["erk-plan", "erk-learn"]
    )

    ctx, _, _, _, _, repo_root = setup_submit_context(tmp_path, {"5652": learn_plan})

    result = get_learn_plan_parent_branch(ctx, repo_root, learn_body)

    assert result is None


def test_get_learn_plan_parent_branch_returns_none_without_parent_branch(tmp_path: Path) -> None:
    """Test get_learn_plan_parent_branch returns None when parent has no branch_name."""
    # Parent plan without branch_name
    parent_body = make_plan_body()  # No branch_name in header
    parent_plan = create_plan("5637", "Add feature", body=parent_body, labels=["erk-plan"])

    # Learn plan referencing parent
    learn_body = _make_learn_plan_body_with_parent(learned_from_issue=5637)
    learn_plan = create_plan(
        "5652", "Extract docs", body=learn_body, labels=["erk-plan", "erk-learn"]
    )

    ctx, _, _, _, _, repo_root = setup_submit_context(
        tmp_path, {"5637": parent_plan, "5652": learn_plan}
    )

    result = get_learn_plan_parent_branch(ctx, repo_root, learn_body)

    assert result is None


def test_submit_learn_plan_uses_parent_branch_when_available(tmp_path: Path) -> None:
    """Test submit uses parent's branch for learn plans when branch exists on remote."""
    # Parent plan with branch_name
    parent_body = _make_parent_plan_body_with_branch("P5637-add-feature-01-23-0433")
    parent_plan = create_plan("5637", "Add feature", body=parent_body, labels=["erk-plan"])

    # Learn plan referencing parent
    learn_body = _make_learn_plan_body_with_parent(learned_from_issue=5637)
    learn_plan = create_plan(
        "5652", "Extract documentation", body=learn_body, labels=["erk-plan", "erk-learn"]
    )

    ctx, fake_git, _, _, _, repo_root = setup_submit_context(
        tmp_path, {"5637": parent_plan, "5652": learn_plan}
    )

    # Configure parent branch to exist on remote (format: {repo_root: ["origin/branch", ...]})
    fake_git._remote_branches = {
        repo_root: ["origin/P5637-add-feature-01-23-0433", "origin/master"]
    }

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["5652"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "Learn plan detected, stacking on parent branch" in result.output
    assert "P5637-add-feature-01-23-0433" in result.output


def test_submit_learn_plan_falls_back_when_parent_branch_not_on_remote(tmp_path: Path) -> None:
    """Test submit falls back to trunk when parent branch is not on remote."""
    # Parent plan with branch_name
    parent_body = _make_parent_plan_body_with_branch("P5637-add-feature-01-23-0433")
    parent_plan = create_plan("5637", "Add feature", body=parent_body, labels=["erk-plan"])

    # Learn plan referencing parent
    learn_body = _make_learn_plan_body_with_parent(learned_from_issue=5637)
    learn_plan = create_plan(
        "5652", "Extract documentation", body=learn_body, labels=["erk-plan", "erk-learn"]
    )

    ctx, fake_git, _, _, _, repo_root = setup_submit_context(
        tmp_path, {"5637": parent_plan, "5652": learn_plan}
    )

    # Parent branch does NOT exist on remote - only master
    fake_git._remote_branches = {repo_root: ["origin/master"]}

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["5652"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "Parent branch 'P5637-add-feature-01-23-0433' not on remote" in result.output


def test_submit_skips_parent_detection_when_base_explicitly_provided(tmp_path: Path) -> None:
    """Test submit skips parent branch detection when --base is explicitly provided."""
    # Parent plan with branch_name
    parent_body = _make_parent_plan_body_with_branch("P5637-add-feature-01-23-0433")
    parent_plan = create_plan("5637", "Add feature", body=parent_body, labels=["erk-plan"])

    # Learn plan referencing parent
    learn_body = _make_learn_plan_body_with_parent(learned_from_issue=5637)
    learn_plan = create_plan(
        "5652", "Extract documentation", body=learn_body, labels=["erk-plan", "erk-learn"]
    )

    ctx, fake_git, _, _, _, repo_root = setup_submit_context(
        tmp_path, {"5637": parent_plan, "5652": learn_plan}
    )

    # Configure branches (custom-base exists on remote)
    fake_git._remote_branches = {
        repo_root: [
            "origin/P5637-add-feature-01-23-0433",
            "origin/master",
            "origin/custom-base",
        ]
    }

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["5652", "--base", "custom-base"], obj=ctx)

    assert result.exit_code == 0, result.output
    # Should NOT mention parent branch detection
    assert "Learn plan detected, stacking on parent branch" not in result.output
