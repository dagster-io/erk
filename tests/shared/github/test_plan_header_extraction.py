"""Tests for PlanHeaderSchema extraction plan fields (plan_type, mixin fields).

Layer 3 (Pure Unit Tests): Tests for plan header schema validation with
zero dependencies.
"""

import pytest

from erk_shared.github.metadata import (
    PlanHeaderSchema,
    create_plan_header_block,
    find_metadata_block,
    format_plan_header_body,
    render_metadata_block,
)

# === Schema Validation Tests ===


def test_plan_header_schema_accepts_standard_plan_type() -> None:
    """Schema accepts plan_type: standard."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "plan_type": "standard",
    }

    # Should not raise
    schema.validate(data)


def test_plan_header_schema_accepts_extraction_plan_type() -> None:
    """Schema accepts plan_type: extraction with required mixin fields."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "plan_type": "extraction",
        "source_plan_issues": [123, 456],
        "extraction_session_ids": ["abc123", "def456"],
    }

    # Should not raise
    schema.validate(data)


def test_plan_header_schema_rejects_invalid_plan_type() -> None:
    """Schema rejects invalid plan_type values."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "plan_type": "invalid",
    }

    with pytest.raises(ValueError, match="Invalid plan_type 'invalid'"):
        schema.validate(data)


def test_plan_header_schema_requires_source_issues_for_extraction() -> None:
    """Schema requires source_plan_issues when plan_type is extraction."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "plan_type": "extraction",
        "extraction_session_ids": ["abc123"],
        # Missing source_plan_issues
    }

    with pytest.raises(ValueError, match="source_plan_issues is required"):
        schema.validate(data)


def test_plan_header_schema_requires_session_ids_for_extraction() -> None:
    """Schema requires extraction_session_ids when plan_type is extraction."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "plan_type": "extraction",
        "source_plan_issues": [123],
        # Missing extraction_session_ids
    }

    with pytest.raises(ValueError, match="extraction_session_ids is required"):
        schema.validate(data)


def test_plan_header_schema_validates_source_issues_are_integers() -> None:
    """Schema validates that source_plan_issues contains only integers."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "source_plan_issues": ["not-an-int"],
    }

    with pytest.raises(ValueError, match="source_plan_issues must contain only integers"):
        schema.validate(data)


def test_plan_header_schema_validates_source_issues_are_positive() -> None:
    """Schema validates that source_plan_issues contains positive integers."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "source_plan_issues": [0],
    }

    with pytest.raises(ValueError, match="source_plan_issues must contain positive integers"):
        schema.validate(data)


def test_plan_header_schema_validates_session_ids_are_strings() -> None:
    """Schema validates that extraction_session_ids contains only strings."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "extraction_session_ids": [123],
    }

    with pytest.raises(ValueError, match="extraction_session_ids must contain only strings"):
        schema.validate(data)


def test_plan_header_schema_validates_session_ids_not_empty() -> None:
    """Schema validates that extraction_session_ids contains no empty strings."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "extraction_session_ids": ["valid", ""],
    }

    with pytest.raises(ValueError, match="extraction_session_ids must not contain empty strings"):
        schema.validate(data)


def test_plan_header_schema_accepts_null_plan_type() -> None:
    """Schema accepts null plan_type (defaults to standard)."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "plan_type": None,
    }

    # Should not raise
    schema.validate(data)


def test_plan_header_schema_accepts_empty_source_issues() -> None:
    """Schema accepts empty source_plan_issues list for extraction plans."""
    schema = PlanHeaderSchema()
    data = {
        "schema_version": "2",
        "created_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "plan_type": "extraction",
        "source_plan_issues": [],  # Empty is valid
        "extraction_session_ids": ["abc123"],
    }

    # Should not raise
    schema.validate(data)


# === Block Creation Tests ===


def test_create_plan_header_block_with_extraction_type() -> None:
    """create_plan_header_block includes extraction fields when provided."""
    block = create_plan_header_block(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        plan_type="extraction",
        source_plan_issues=[123, 456],
        extraction_session_ids=["abc123", "def456"],
        objective_issue=None,
    )

    assert block.key == "plan-header"
    assert block.data["plan_type"] == "extraction"
    assert block.data["source_plan_issues"] == [123, 456]
    assert block.data["extraction_session_ids"] == ["abc123", "def456"]


def test_create_plan_header_block_without_extraction_type() -> None:
    """create_plan_header_block omits extraction fields when not provided."""
    block = create_plan_header_block(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        plan_type=None,
        source_plan_issues=None,
        extraction_session_ids=None,
        objective_issue=None,
    )

    assert block.key == "plan-header"
    assert "plan_type" not in block.data
    assert "source_plan_issues" not in block.data
    assert "extraction_session_ids" not in block.data


# === Format/Render Tests ===


def test_format_plan_header_body_with_extraction() -> None:
    """format_plan_header_body includes extraction fields in rendered output."""
    body = format_plan_header_body(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        plan_type="extraction",
        source_plan_issues=[123],
        extraction_session_ids=["abc123"],
        objective_issue=None,
    )

    # Verify the block can be parsed back
    block = find_metadata_block(body, "plan-header")
    assert block is not None
    assert block.data["plan_type"] == "extraction"
    assert block.data["source_plan_issues"] == [123]
    assert block.data["extraction_session_ids"] == ["abc123"]


def test_render_and_extract_extraction_plan_header() -> None:
    """Render and extract round-trip preserves extraction fields."""
    block = create_plan_header_block(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        worktree_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        plan_type="extraction",
        source_plan_issues=[100, 200],
        extraction_session_ids=["session-1", "session-2"],
        objective_issue=None,
    )

    rendered = render_metadata_block(block)
    extracted = find_metadata_block(rendered, "plan-header")

    assert extracted is not None
    assert extracted.data["plan_type"] == "extraction"
    assert extracted.data["source_plan_issues"] == [100, 200]
    assert extracted.data["extraction_session_ids"] == ["session-1", "session-2"]
