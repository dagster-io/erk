"""Tests for PlanIssueSchema and create_plan_issue_block."""

import pytest

from erk_shared.gateway.github.metadata_blocks import (
    PlanIssueSchema,
    create_plan_issue_block,
    render_erk_issue_event,
)

# === PlanIssueSchema Tests ===


def test_plan_issue_schema_validates_valid_data() -> None:
    """Test PlanIssueSchema accepts valid data."""
    schema = PlanIssueSchema()
    data = {
        "issue_number": 123,
        "worktree_name": "add-user-auth",
        "timestamp": "2025-11-22T12:00:00Z",
        "plan_file": "add-user-auth-plan.md",
    }
    schema.validate(data)  # Should not raise


def test_plan_issue_schema_validates_without_plan_file() -> None:
    """Test PlanIssueSchema accepts data without optional plan_file."""
    schema = PlanIssueSchema()
    data = {
        "issue_number": 456,
        "worktree_name": "fix-bug",
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise


def test_plan_issue_schema_rejects_missing_required_field() -> None:
    """Test PlanIssueSchema rejects missing required fields."""
    schema = PlanIssueSchema()
    data = {
        "issue_number": 123,
        # missing worktree_name
        "timestamp": "2025-11-22T12:00:00Z",
    }
    with pytest.raises(ValueError, match="Missing required fields: worktree_name"):
        schema.validate(data)


def test_plan_issue_schema_rejects_non_positive_issue_number() -> None:
    """Test PlanIssueSchema rejects non-positive issue_number."""
    schema = PlanIssueSchema()
    data = {
        "issue_number": 0,
        "worktree_name": "test",
        "timestamp": "2025-11-22T12:00:00Z",
    }
    with pytest.raises(ValueError, match="issue_number must be positive"):
        schema.validate(data)


def test_plan_issue_schema_get_key() -> None:
    """Test PlanIssueSchema returns correct key."""
    schema = PlanIssueSchema()
    assert schema.get_key() == "erk-plan"


# === create_plan_issue_block Tests ===


def test_create_plan_issue_block_with_plan_file() -> None:
    """Test create_plan_issue_block with plan_file."""
    block = create_plan_issue_block(
        issue_number=123,
        worktree_name="add-user-auth",
        timestamp="2025-11-22T12:00:00Z",
        plan_file="add-user-auth-plan.md",
    )
    assert block.key == "erk-plan"
    assert block.data["issue_number"] == 123
    assert block.data["worktree_name"] == "add-user-auth"
    assert block.data["plan_file"] == "add-user-auth-plan.md"


def test_create_plan_issue_block_without_plan_file() -> None:
    """Test create_plan_issue_block without plan_file."""
    block = create_plan_issue_block(
        issue_number=456,
        worktree_name="fix-bug",
        timestamp="2025-11-22T12:00:00Z",
    )
    assert block.key == "erk-plan"
    assert "plan_file" not in block.data


# === render_erk_issue_event with plan issue Tests ===


def test_render_erk_issue_event_with_plan_issue_block() -> None:
    """Test render_erk_issue_event with plan issue block and workflow instructions."""
    block = create_plan_issue_block(
        issue_number=123,
        worktree_name="add-user-auth",
        timestamp="2025-11-22T12:00:00Z",
    )

    plan_content = "# Plan\n\n1. Step one\n2. Step two"
    workflow = (
        "## Quick Start\n\n```bash\n"
        'claude --permission-mode acceptEdits -p "/erk:create-wt-from-plan-issue '
        '#123 add-user-auth"\n```'
    )
    description = f"{plan_content}\n\n---\n\n{workflow}"

    comment = render_erk_issue_event(
        title="📋 Add User Authentication",
        metadata=block,
        description=description,
    )

    # Verify structure
    assert comment.startswith("📋 Add User Authentication\n\n")
    assert "<!-- erk:metadata-block:erk-plan -->" in comment
    assert "issue_number: 123" in comment
    assert "worktree_name: add-user-auth" in comment
    assert plan_content in comment
    assert workflow in comment
