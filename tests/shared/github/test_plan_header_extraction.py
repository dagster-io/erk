"""Tests for PlanHeaderSchema validation.

Layer 3 (Pure Unit Tests): Tests for plan header schema validation with
zero dependencies.
"""

import pytest

from erk_shared.gateway.github.metadata.core import find_metadata_block, render_metadata_block
from erk_shared.gateway.github.metadata.plan_header import (
    create_plan_header_block,
    extract_plan_header_branch_name,
    extract_plan_header_last_learn_at,
    extract_plan_header_last_learn_session,
    extract_plan_header_learn_plan_issue,
    extract_plan_header_learn_plan_pr,
    extract_plan_header_learn_status,
    extract_plan_header_learned_from_issue,
    extract_plan_header_objective_issue,
    extract_plan_header_remote_impl_run_id,
    extract_plan_header_remote_impl_session_id,
    update_plan_header_learn_event,
    update_plan_header_learn_plan_completed,
    update_plan_header_learn_result,
    update_plan_header_learn_status,
    update_plan_header_remote_impl_event,
    update_plan_header_worktree_and_branch,
)
from erk_shared.gateway.github.metadata.schemas import PlanHeaderSchema
from tests.test_utils.plan_helpers import format_plan_header_body_for_test

# === Schema Validation Tests ===


def test_plan_header_schema_accepts_minimal_data() -> None:
    """Schema accepts minimal required fields."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
    }

    # Should not raise
    schema.validate(data)


def test_plan_header_schema_accepts_source_repo() -> None:
    """Schema accepts source_repo for cross-repo plans."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "source_repo": "owner/repo",
    }

    # Should not raise
    schema.validate(data)


def test_plan_header_schema_accepts_objective_issue() -> None:
    """Schema accepts objective_issue reference."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "objective_issue": 42,
    }

    # Should not raise
    schema.validate(data)


def test_plan_header_schema_accepts_created_from_session() -> None:
    """Schema accepts created_from_session for learn discovery."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "created_from_session": "abc-123-session-id",
    }

    # Should not raise
    schema.validate(data)


def test_plan_header_schema_accepts_all_optional_fields() -> None:
    """Schema accepts all optional fields together."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "worktree_name": "my-worktree",
        "plan_comment_id": 12345,
        "last_dispatched_run_id": "run-123",
        "last_dispatched_node_id": "node-456",
        "last_dispatched_at": "2024-01-15T11:00:00Z",
        "source_repo": "owner/repo",
        "objective_issue": 42,
        "created_from_session": "session-abc",
    }

    # Should not raise
    schema.validate(data)


def test_plan_header_schema_rejects_missing_schema_version() -> None:
    """Schema rejects data without schema_version."""
    schema = PlanHeaderSchema()
    data = {
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
    }

    with pytest.raises(ValueError, match="Missing required fields: schema_version"):
        schema.validate(data)


def test_plan_header_schema_rejects_missing_created_at() -> None:
    """Schema rejects data without created_at."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_by": "user123",
    }

    with pytest.raises(ValueError, match="Missing required fields: created_at"):
        schema.validate(data)


def test_plan_header_schema_rejects_missing_created_by() -> None:
    """Schema rejects data without created_by."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
    }

    with pytest.raises(ValueError, match="Missing required fields: created_by"):
        schema.validate(data)


# === Block Creation Tests ===


def test_create_plan_header_block_minimal() -> None:
    """create_plan_header_block creates block with minimal fields."""
    block = create_plan_header_block(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
    )

    assert block.key == "plan-header"
    assert block.data["schema_version"] == "2"
    assert block.data["created_at"] == "2024-01-15T10:30:00Z"
    assert block.data["created_by"] == "user123"


def test_create_plan_header_block_with_optional_fields() -> None:
    """create_plan_header_block includes optional fields when provided."""
    block = create_plan_header_block(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name="my-worktree",
        branch_name="feature-branch",
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo="owner/repo",
        objective_issue=42,
        created_from_session="session-abc",
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
    )

    assert block.key == "plan-header"
    assert block.data["worktree_name"] == "my-worktree"
    assert block.data["branch_name"] == "feature-branch"
    assert block.data["source_repo"] == "owner/repo"
    assert block.data["objective_issue"] == 42
    assert block.data["created_from_session"] == "session-abc"


def test_create_plan_header_block_omits_none_values() -> None:
    """create_plan_header_block omits fields set to None."""
    block = create_plan_header_block(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
    )

    assert block.key == "plan-header"
    assert "worktree_name" not in block.data
    assert "branch_name" not in block.data
    assert "source_repo" not in block.data
    assert "objective_issue" not in block.data


# === Format/Render Tests ===


def test_format_plan_header_body_minimal() -> None:
    """format_plan_header_body creates valid body with minimal fields."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    # Verify the block can be parsed back
    block = find_metadata_block(body, "plan-header")
    assert block is not None
    assert block.data["schema_version"] == "2"
    assert block.data["created_at"] == "2024-01-15T10:30:00Z"
    assert block.data["created_by"] == "user123"


def test_format_plan_header_body_with_optional_fields() -> None:
    """format_plan_header_body includes optional fields in rendered output."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name="feature-branch",
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo="owner/repo",
        objective_issue=42,
        created_from_session="session-abc",
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    # Verify the block can be parsed back
    block = find_metadata_block(body, "plan-header")
    assert block is not None
    assert block.data["branch_name"] == "feature-branch"
    assert block.data["source_repo"] == "owner/repo"
    assert block.data["objective_issue"] == 42
    assert block.data["created_from_session"] == "session-abc"


def test_render_and_extract_round_trip() -> None:
    """Render and extract round-trip preserves all fields."""
    block = create_plan_header_block(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name="my-worktree",
        branch_name="feature-branch",
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo="owner/repo",
        objective_issue=100,
        created_from_session="session-xyz",
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
    )

    rendered = render_metadata_block(block)
    extracted = find_metadata_block(rendered, "plan-header")

    assert extracted is not None
    assert extracted.data["schema_version"] == "2"
    assert extracted.data["created_at"] == "2024-01-15T10:30:00Z"
    assert extracted.data["created_by"] == "user123"
    assert extracted.data["worktree_name"] == "my-worktree"
    assert extracted.data["branch_name"] == "feature-branch"
    assert extracted.data["source_repo"] == "owner/repo"
    assert extracted.data["objective_issue"] == 100
    assert extracted.data["created_from_session"] == "session-xyz"


# === Learn Field Tests ===


def test_plan_header_schema_accepts_learn_fields() -> None:
    """Schema accepts last_learn_session and last_learn_at fields."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "last_learn_session": "learn-session-123",
        "last_learn_at": "2024-01-16T14:00:00Z",
    }

    # Should not raise
    schema.validate(data)


def test_plan_header_schema_rejects_empty_learn_session() -> None:
    """Schema rejects empty last_learn_session."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "last_learn_session": "",
    }

    with pytest.raises(ValueError, match="last_learn_session must not be empty"):
        schema.validate(data)


def test_plan_header_schema_rejects_empty_learn_at() -> None:
    """Schema rejects empty last_learn_at."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "last_learn_at": "",
    }

    with pytest.raises(ValueError, match="last_learn_at must not be empty"):
        schema.validate(data)


def test_create_plan_header_block_with_learn_fields() -> None:
    """create_plan_header_block includes learn fields when provided."""
    block = create_plan_header_block(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session="learn-session-abc",
        last_learn_at="2024-01-16T14:00:00Z",
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
    )

    assert block.key == "plan-header"
    assert block.data["last_learn_session"] == "learn-session-abc"
    assert block.data["last_learn_at"] == "2024-01-16T14:00:00Z"


def test_format_plan_header_body_with_learn_fields() -> None:
    """format_plan_header_body includes learn fields in rendered output."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session="learn-session-xyz",
        last_learn_at="2024-01-16T15:00:00Z",
        learn_status=None,
    )

    # Verify the block can be parsed back
    block = find_metadata_block(body, "plan-header")
    assert block is not None
    assert block.data["last_learn_session"] == "learn-session-xyz"
    assert block.data["last_learn_at"] == "2024-01-16T15:00:00Z"


def test_update_plan_header_learn_event() -> None:
    """update_plan_header_learn_event updates learn fields atomically."""
    # Create initial body
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    # Update with learn event
    updated_body = update_plan_header_learn_event(
        issue_body=body,
        learn_at="2024-01-16T14:00:00Z",
        session_id="learn-session-new",
    )

    # Verify the block was updated
    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data["last_learn_at"] == "2024-01-16T14:00:00Z"
    assert block.data["last_learn_session"] == "learn-session-new"
    # Original fields preserved
    assert block.data["created_at"] == "2024-01-15T10:30:00Z"
    assert block.data["created_by"] == "user123"


def test_update_plan_header_learn_event_with_none_session() -> None:
    """update_plan_header_learn_event handles None session_id."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    updated_body = update_plan_header_learn_event(
        issue_body=body,
        learn_at="2024-01-16T14:00:00Z",
        session_id=None,
    )

    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data["last_learn_at"] == "2024-01-16T14:00:00Z"
    assert block.data["last_learn_session"] is None


def test_update_plan_header_learn_event_raises_for_missing_block() -> None:
    """update_plan_header_learn_event raises ValueError if no plan-header block."""
    body = "Some other content without plan-header"

    with pytest.raises(ValueError, match="plan-header block not found"):
        update_plan_header_learn_event(
            issue_body=body,
            learn_at="2024-01-16T14:00:00Z",
            session_id="session-123",
        )


def test_extract_plan_header_last_learn_session() -> None:
    """extract_plan_header_last_learn_session extracts session from body."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session="learn-session-extract",
        last_learn_at=None,
        learn_status=None,
    )

    session_id = extract_plan_header_last_learn_session(body)
    assert session_id == "learn-session-extract"


def test_extract_plan_header_last_learn_session_returns_none_when_missing() -> None:
    """extract_plan_header_last_learn_session returns None when field is absent."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    session_id = extract_plan_header_last_learn_session(body)
    assert session_id is None


def test_extract_plan_header_last_learn_session_returns_none_for_invalid_body() -> None:
    """extract_plan_header_last_learn_session returns None for invalid body."""
    body = "No metadata block here"

    session_id = extract_plan_header_last_learn_session(body)
    assert session_id is None


def test_extract_plan_header_last_learn_at() -> None:
    """extract_plan_header_last_learn_at extracts timestamp from body."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at="2024-01-16T14:00:00Z",
        learn_status=None,
    )

    timestamp = extract_plan_header_last_learn_at(body)
    assert timestamp == "2024-01-16T14:00:00Z"


def test_extract_plan_header_last_learn_at_returns_none_when_missing() -> None:
    """extract_plan_header_last_learn_at returns None when field is absent."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    timestamp = extract_plan_header_last_learn_at(body)
    assert timestamp is None


# === Branch Name Field Tests ===


def test_plan_header_schema_accepts_branch_name() -> None:
    """Schema accepts branch_name field."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "branch_name": "feature-branch",
    }

    # Should not raise
    schema.validate(data)


def test_plan_header_schema_rejects_empty_branch_name() -> None:
    """Schema rejects empty branch_name."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "branch_name": "",
    }

    with pytest.raises(ValueError, match="branch_name must not be empty"):
        schema.validate(data)


def test_extract_plan_header_branch_name() -> None:
    """extract_plan_header_branch_name extracts branch from body."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name="feature-branch",
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    branch = extract_plan_header_branch_name(body)
    assert branch == "feature-branch"


def test_extract_plan_header_branch_name_returns_none_when_missing() -> None:
    """extract_plan_header_branch_name returns None when field is absent."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    branch = extract_plan_header_branch_name(body)
    assert branch is None


def test_extract_plan_header_branch_name_returns_none_for_invalid_body() -> None:
    """extract_plan_header_branch_name returns None for invalid body."""
    body = "No metadata block here"

    branch = extract_plan_header_branch_name(body)
    assert branch is None


def test_update_plan_header_worktree_and_branch() -> None:
    """update_plan_header_worktree_and_branch updates both fields atomically."""
    # Create initial body without worktree or branch
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    # Update with worktree and branch
    updated_body = update_plan_header_worktree_and_branch(
        issue_body=body,
        worktree_name="my-worktree",
        branch_name="feature-branch",
    )

    # Verify the block was updated
    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data["worktree_name"] == "my-worktree"
    assert block.data["branch_name"] == "feature-branch"
    # Original fields preserved
    assert block.data["created_at"] == "2024-01-15T10:30:00Z"
    assert block.data["created_by"] == "user123"


def test_update_plan_header_worktree_and_branch_raises_for_missing_block() -> None:
    """update_plan_header_worktree_and_branch raises ValueError if no plan-header."""
    body = "Some other content without plan-header"

    with pytest.raises(ValueError, match="plan-header block not found"):
        update_plan_header_worktree_and_branch(
            issue_body=body,
            worktree_name="my-worktree",
            branch_name="feature-branch",
        )


# === Objective Issue Extraction Tests ===


def test_extract_plan_header_objective_issue() -> None:
    """extract_plan_header_objective_issue extracts objective from body."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=42,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    result = extract_plan_header_objective_issue(body)
    assert result == 42


def test_extract_plan_header_objective_issue_returns_none_when_missing() -> None:
    """extract_plan_header_objective_issue returns None when field is absent."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    result = extract_plan_header_objective_issue(body)
    assert result is None


def test_extract_plan_header_objective_issue_returns_none_for_plan_content() -> None:
    """extract_plan_header_objective_issue returns None for plan content without metadata.

    This test verifies the fix for a bug where objective_issue was extracted from
    plan.body (which contains plan content) instead of plan.metadata["issue_body"]
    (which contains the issue body with plan-header metadata block).

    Plan content typically looks like markdown without metadata blocks, so extraction
    should return None rather than incorrectly parsing the content.
    """
    # Simulate plan content (what's in plan.body from GitHubPlanStore)
    plan_content = """# Plan: Add Feature X

## Summary
Implement feature X to do Y.

## Implementation Steps
1. Step one
2. Step two

## Test Plan
- Unit tests for new functionality
"""

    result = extract_plan_header_objective_issue(plan_content)
    assert result is None


def test_extract_plan_header_objective_issue_returns_none_for_invalid_body() -> None:
    """extract_plan_header_objective_issue returns None for body without metadata block."""
    body = "No metadata block here"

    result = extract_plan_header_objective_issue(body)
    assert result is None


# === Remote Implementation Field Tests ===


def test_create_plan_header_block_with_remote_impl_fields() -> None:
    """create_plan_header_block includes remote impl fields when provided."""
    block = create_plan_header_block(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at="2024-01-15T14:00:00Z",
        last_remote_impl_run_id="12345678",
        last_remote_impl_session_id="remote-session-abc",
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
    )

    assert block.key == "plan-header"
    assert block.data["last_remote_impl_at"] == "2024-01-15T14:00:00Z"
    assert block.data["last_remote_impl_run_id"] == "12345678"
    assert block.data["last_remote_impl_session_id"] == "remote-session-abc"


def test_extract_plan_header_remote_impl_run_id() -> None:
    """extract_plan_header_remote_impl_run_id extracts run ID from body."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id="run-12345",
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    run_id = extract_plan_header_remote_impl_run_id(body)
    assert run_id == "run-12345"


def test_extract_plan_header_remote_impl_run_id_returns_none_when_missing() -> None:
    """extract_plan_header_remote_impl_run_id returns None when field is absent."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    run_id = extract_plan_header_remote_impl_run_id(body)
    assert run_id is None


def test_extract_plan_header_remote_impl_run_id_returns_none_for_invalid_body() -> None:
    """extract_plan_header_remote_impl_run_id returns None for invalid body."""
    body = "No metadata block here"

    run_id = extract_plan_header_remote_impl_run_id(body)
    assert run_id is None


def test_extract_plan_header_remote_impl_session_id() -> None:
    """extract_plan_header_remote_impl_session_id extracts session ID from body."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id="remote-session-xyz",
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    session_id = extract_plan_header_remote_impl_session_id(body)
    assert session_id == "remote-session-xyz"


def test_extract_plan_header_remote_impl_session_id_returns_none_when_missing() -> None:
    """extract_plan_header_remote_impl_session_id returns None when field is absent."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    session_id = extract_plan_header_remote_impl_session_id(body)
    assert session_id is None


def test_update_plan_header_remote_impl_event() -> None:
    """update_plan_header_remote_impl_event updates all remote impl fields atomically."""
    # Create initial body
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    # Update with remote impl event
    updated_body = update_plan_header_remote_impl_event(
        issue_body=body,
        run_id="remote-run-123",
        session_id="remote-session-abc",
        remote_impl_at="2024-01-16T14:00:00Z",
    )

    # Verify the block was updated
    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data["last_remote_impl_at"] == "2024-01-16T14:00:00Z"
    assert block.data["last_remote_impl_run_id"] == "remote-run-123"
    assert block.data["last_remote_impl_session_id"] == "remote-session-abc"
    # Original fields preserved
    assert block.data["created_at"] == "2024-01-15T10:30:00Z"
    assert block.data["created_by"] == "user123"


def test_update_plan_header_remote_impl_event_with_none_session() -> None:
    """update_plan_header_remote_impl_event handles None session_id."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    updated_body = update_plan_header_remote_impl_event(
        issue_body=body,
        run_id="remote-run-456",
        session_id=None,
        remote_impl_at="2024-01-16T15:00:00Z",
    )

    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data["last_remote_impl_at"] == "2024-01-16T15:00:00Z"
    assert block.data["last_remote_impl_run_id"] == "remote-run-456"
    assert block.data["last_remote_impl_session_id"] is None


def test_update_plan_header_remote_impl_event_raises_for_missing_block() -> None:
    """update_plan_header_remote_impl_event raises ValueError if no plan-header block."""
    body = "Some other content without plan-header"

    with pytest.raises(ValueError, match="plan-header block not found"):
        update_plan_header_remote_impl_event(
            issue_body=body,
            run_id="remote-run-123",
            session_id="session-123",
            remote_impl_at="2024-01-16T14:00:00Z",
        )


# === Learn Status Tests ===


def test_plan_header_schema_accepts_learn_status_pending() -> None:
    """Schema accepts learn_status with value 'pending'."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "learn_status": "pending",
    }

    # Should not raise
    schema.validate(data)


def test_plan_header_schema_accepts_learn_status_null() -> None:
    """Schema accepts learn_status with value null."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "learn_status": None,
    }

    # Should not raise
    schema.validate(data)


def test_plan_header_schema_rejects_invalid_learn_status() -> None:
    """Schema rejects learn_status with invalid value."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "learn_status": "invalid",
    }

    with pytest.raises(ValueError, match="learn_status must be one of"):
        schema.validate(data)


def test_extract_plan_header_learn_status() -> None:
    """extract_plan_header_learn_status extracts status from body."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status="pending",
    )

    status = extract_plan_header_learn_status(body)
    assert status == "pending"


def test_extract_plan_header_learn_status_returns_none_when_missing() -> None:
    """extract_plan_header_learn_status returns None when field is absent."""
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    status = extract_plan_header_learn_status(body)
    assert status is None


def test_extract_plan_header_learn_status_returns_none_for_invalid_body() -> None:
    """extract_plan_header_learn_status returns None for invalid body."""
    body = "No metadata block here"

    status = extract_plan_header_learn_status(body)
    assert status is None


def test_update_plan_header_learn_status() -> None:
    """update_plan_header_learn_status updates learn_status field."""
    # Create initial body without learn_status
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )

    # Update with learn_status
    updated_body = update_plan_header_learn_status(
        issue_body=body,
        learn_status="pending",
    )

    # Verify the block was updated
    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data["learn_status"] == "pending"
    # Original fields preserved
    assert block.data["created_at"] == "2024-01-15T10:30:00Z"
    assert block.data["created_by"] == "user123"


def test_update_plan_header_learn_status_to_not_started() -> None:
    """update_plan_header_learn_status can update from pending to not_started."""
    # Create initial body with pending status
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status="pending",
    )

    # Update to not_started (testing status update mechanism works)
    updated_body = update_plan_header_learn_status(
        issue_body=body,
        learn_status="not_started",
    )

    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data["learn_status"] == "not_started"


def test_update_plan_header_learn_status_raises_for_missing_block() -> None:
    """update_plan_header_learn_status raises ValueError if no plan-header block."""
    body = "Some other content without plan-header"

    with pytest.raises(ValueError, match="plan-header block not found"):
        update_plan_header_learn_status(
            issue_body=body,
            learn_status="pending",
        )


# === New Learn Status Infrastructure Tests ===


def test_plan_header_schema_accepts_new_learn_status_values() -> None:
    """Schema accepts all new learn_status values."""
    schema = PlanHeaderSchema()
    base_data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
    }

    # All valid status values
    valid_statuses = [
        "not_started",
        "pending",
        "completed_no_plan",
        "completed_with_plan",
        "plan_completed",
    ]

    for status in valid_statuses:
        data = {**base_data, "learn_status": status}
        schema.validate(data)  # Should not raise


def test_plan_header_schema_accepts_learn_plan_issue() -> None:
    """Schema accepts learn_plan_issue field."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "learn_plan_issue": 456,
    }

    schema.validate(data)  # Should not raise


def test_plan_header_schema_accepts_learn_plan_pr() -> None:
    """Schema accepts learn_plan_pr field."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "learn_plan_pr": 789,
    }

    schema.validate(data)  # Should not raise


def test_plan_header_schema_accepts_learned_from_issue() -> None:
    """Schema accepts learned_from_issue field."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "learned_from_issue": 123,
    }

    schema.validate(data)  # Should not raise


def test_plan_header_schema_rejects_invalid_int_fields() -> None:
    """Schema rejects non-positive integers for new fields."""
    schema = PlanHeaderSchema()
    base_data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
    }

    # Test each field with invalid values
    for field, msg in [
        ("learn_plan_issue", "learn_plan_issue must be positive"),
        ("learn_plan_pr", "learn_plan_pr must be positive"),
        ("learned_from_issue", "learned_from_issue must be positive"),
    ]:
        data = {**base_data, field: 0}
        with pytest.raises(ValueError, match=msg):
            schema.validate(data)

        data = {**base_data, field: -1}
        with pytest.raises(ValueError, match=msg):
            schema.validate(data)


def test_extract_plan_header_learn_plan_issue() -> None:
    """extract_plan_header_learn_plan_issue returns the value."""
    body = format_plan_header_body_for_test(learn_plan_issue=456)

    result = extract_plan_header_learn_plan_issue(body)
    assert result == 456


def test_extract_plan_header_learn_plan_issue_returns_none_if_missing() -> None:
    """extract_plan_header_learn_plan_issue returns None when field not set."""
    body = format_plan_header_body_for_test()

    result = extract_plan_header_learn_plan_issue(body)
    assert result is None


def test_extract_plan_header_learn_plan_pr() -> None:
    """extract_plan_header_learn_plan_pr returns the value."""
    body = format_plan_header_body_for_test(learn_plan_pr=789)

    result = extract_plan_header_learn_plan_pr(body)
    assert result == 789


def test_extract_plan_header_learn_plan_pr_returns_none_if_missing() -> None:
    """extract_plan_header_learn_plan_pr returns None when field not set."""
    body = format_plan_header_body_for_test()

    result = extract_plan_header_learn_plan_pr(body)
    assert result is None


def test_extract_plan_header_learned_from_issue() -> None:
    """extract_plan_header_learned_from_issue returns the value."""
    body = format_plan_header_body_for_test(learned_from_issue=123)

    result = extract_plan_header_learned_from_issue(body)
    assert result == 123


def test_extract_plan_header_learned_from_issue_returns_none_if_missing() -> None:
    """extract_plan_header_learned_from_issue returns None when field not set."""
    body = format_plan_header_body_for_test()

    result = extract_plan_header_learned_from_issue(body)
    assert result is None


def test_update_plan_header_learn_result_completed_no_plan() -> None:
    """update_plan_header_learn_result sets status to completed_no_plan."""
    body = format_plan_header_body_for_test(learn_status="pending")

    updated_body = update_plan_header_learn_result(
        issue_body=body,
        learn_status="completed_no_plan",
        learn_plan_issue=None,
    )

    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data["learn_status"] == "completed_no_plan"
    assert "learn_plan_issue" not in block.data or block.data.get("learn_plan_issue") is None


def test_update_plan_header_learn_result_completed_with_plan() -> None:
    """update_plan_header_learn_result sets status and learn_plan_issue."""
    body = format_plan_header_body_for_test(learn_status="pending")

    updated_body = update_plan_header_learn_result(
        issue_body=body,
        learn_status="completed_with_plan",
        learn_plan_issue=456,
    )

    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data["learn_status"] == "completed_with_plan"
    assert block.data["learn_plan_issue"] == 456


def test_update_plan_header_learn_result_raises_for_missing_block() -> None:
    """update_plan_header_learn_result raises ValueError if no plan-header."""
    body = "Some content without plan-header"

    with pytest.raises(ValueError, match="plan-header block not found"):
        update_plan_header_learn_result(
            issue_body=body,
            learn_status="completed_no_plan",
            learn_plan_issue=None,
        )


def test_update_plan_header_learn_plan_completed() -> None:
    """update_plan_header_learn_plan_completed sets status and PR number."""
    body = format_plan_header_body_for_test(
        learn_status="completed_with_plan",
        learn_plan_issue=456,
    )

    updated_body = update_plan_header_learn_plan_completed(
        issue_body=body,
        learn_plan_pr=789,
    )

    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data["learn_status"] == "plan_completed"
    assert block.data["learn_plan_pr"] == 789


def test_update_plan_header_learn_plan_completed_raises_for_missing_block() -> None:
    """update_plan_header_learn_plan_completed raises ValueError if no plan-header."""
    body = "Some content without plan-header"

    with pytest.raises(ValueError, match="plan-header block not found"):
        update_plan_header_learn_plan_completed(
            issue_body=body,
            learn_plan_pr=789,
        )
