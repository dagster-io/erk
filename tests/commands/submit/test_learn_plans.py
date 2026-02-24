"""Tests for learn plan handling in submit."""

from pathlib import Path

from erk.cli.commands.submit import get_learn_plan_parent_branch, is_issue_learn_plan
from erk_shared.gateway.github.metadata.core import render_metadata_block
from erk_shared.gateway.github.metadata.types import MetadataBlock
from tests.commands.submit.conftest import (
    create_plan,
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

    result = get_learn_plan_parent_branch(ctx, repo_root, "5652")

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

    result = get_learn_plan_parent_branch(ctx, repo_root, "5652")

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

    result = get_learn_plan_parent_branch(ctx, repo_root, "5652")

    assert result is None
