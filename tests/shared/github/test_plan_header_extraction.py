"""Tests for PlanHeaderSchema validation.

Layer 3 (Pure Unit Tests): Tests for plan header schema validation with
zero dependencies.
"""

import pytest

from erk_shared.github.metadata.core import find_metadata_block, render_metadata_block
from erk_shared.github.metadata.plan_header import (
    create_plan_header_block,
    extract_plan_header_last_learn_at,
    extract_plan_header_last_learn_session,
    format_plan_header_body,
    update_plan_header_learn_event,
)
from erk_shared.github.metadata.schemas import PlanHeaderSchema

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
        source_repo="owner/repo",
        objective_issue=42,
        created_from_session="session-abc",
    )

    assert block.key == "plan-header"
    assert block.data["worktree_name"] == "my-worktree"
    assert block.data["source_repo"] == "owner/repo"
    assert block.data["objective_issue"] == 42
    assert block.data["created_from_session"] == "session-abc"


def test_create_plan_header_block_omits_none_values() -> None:
    """create_plan_header_block omits fields set to None."""
    block = create_plan_header_block(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        source_repo=None,
        objective_issue=None,
    )

    assert block.key == "plan-header"
    assert "worktree_name" not in block.data
    assert "source_repo" not in block.data
    assert "objective_issue" not in block.data


# === Format/Render Tests ===


def test_format_plan_header_body_minimal() -> None:
    """format_plan_header_body creates valid body with minimal fields."""
    body = format_plan_header_body(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
    )

    # Verify the block can be parsed back
    block = find_metadata_block(body, "plan-header")
    assert block is not None
    assert block.data["schema_version"] == "2"
    assert block.data["created_at"] == "2024-01-15T10:30:00Z"
    assert block.data["created_by"] == "user123"


def test_format_plan_header_body_with_optional_fields() -> None:
    """format_plan_header_body includes optional fields in rendered output."""
    body = format_plan_header_body(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        source_repo="owner/repo",
        objective_issue=42,
        created_from_session="session-abc",
    )

    # Verify the block can be parsed back
    block = find_metadata_block(body, "plan-header")
    assert block is not None
    assert block.data["source_repo"] == "owner/repo"
    assert block.data["objective_issue"] == 42
    assert block.data["created_from_session"] == "session-abc"


def test_render_and_extract_round_trip() -> None:
    """Render and extract round-trip preserves all fields."""
    block = create_plan_header_block(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name="my-worktree",
        source_repo="owner/repo",
        objective_issue=100,
        created_from_session="session-xyz",
    )

    rendered = render_metadata_block(block)
    extracted = find_metadata_block(rendered, "plan-header")

    assert extracted is not None
    assert extracted.data["schema_version"] == "2"
    assert extracted.data["created_at"] == "2024-01-15T10:30:00Z"
    assert extracted.data["created_by"] == "user123"
    assert extracted.data["worktree_name"] == "my-worktree"
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
        last_learn_session="learn-session-abc",
        last_learn_at="2024-01-16T14:00:00Z",
    )

    assert block.key == "plan-header"
    assert block.data["last_learn_session"] == "learn-session-abc"
    assert block.data["last_learn_at"] == "2024-01-16T14:00:00Z"


def test_format_plan_header_body_with_learn_fields() -> None:
    """format_plan_header_body includes learn fields in rendered output."""
    body = format_plan_header_body(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        last_learn_session="learn-session-xyz",
        last_learn_at="2024-01-16T15:00:00Z",
    )

    # Verify the block can be parsed back
    block = find_metadata_block(body, "plan-header")
    assert block is not None
    assert block.data["last_learn_session"] == "learn-session-xyz"
    assert block.data["last_learn_at"] == "2024-01-16T15:00:00Z"


def test_update_plan_header_learn_event() -> None:
    """update_plan_header_learn_event updates learn fields atomically."""
    # Create initial body
    body = format_plan_header_body(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
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
    body = format_plan_header_body(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
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
    body = format_plan_header_body(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        last_learn_session="learn-session-extract",
    )

    session_id = extract_plan_header_last_learn_session(body)
    assert session_id == "learn-session-extract"


def test_extract_plan_header_last_learn_session_returns_none_when_missing() -> None:
    """extract_plan_header_last_learn_session returns None when field is absent."""
    body = format_plan_header_body(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
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
    body = format_plan_header_body(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        last_learn_at="2024-01-16T14:00:00Z",
    )

    timestamp = extract_plan_header_last_learn_at(body)
    assert timestamp == "2024-01-16T14:00:00Z"


def test_extract_plan_header_last_learn_at_returns_none_when_missing() -> None:
    """extract_plan_header_last_learn_at returns None when field is absent."""
    body = format_plan_header_body(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
    )

    timestamp = extract_plan_header_last_learn_at(body)
    assert timestamp is None
