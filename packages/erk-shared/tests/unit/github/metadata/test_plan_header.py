"""Tests for plan_header.py - Schema v2 plan header operations.

Tests update and extract functions for plan-header metadata fields.
"""

import pytest

from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_header_review_pr,
    update_plan_header_review_pr,
)


def make_plan_header_body(
    review_pr: int | None = None,
) -> str:
    """Create a test issue body with plan-header metadata block.

    Args:
        review_pr: Optional PR number for review_pr field

    Returns:
        Issue body with plan-header metadata block
    """
    review_pr_line = f"review_pr: {review_pr}" if review_pr is not None else "review_pr: null"

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-11-25T14:37:43.513418+00:00'
created_by: testuser
plan_comment_id: 123456789
last_dispatched_run_id: null
last_dispatched_at: null
{review_pr_line}

```

</details>
<!-- /erk:metadata-block:plan-header -->"""


# ============================================================================
# update_plan_header_review_pr Tests
# ============================================================================


def test_update_plan_header_review_pr() -> None:
    """Test updating review_pr field in plan-header."""
    body = make_plan_header_body(review_pr=None)

    updated_body = update_plan_header_review_pr(body, 42)

    # Verify the field was updated
    assert "review_pr: 42" in updated_body
    assert "review_pr: null" not in updated_body


def test_update_plan_header_review_pr_overwrites_existing() -> None:
    """Test updating review_pr field when it already has a value."""
    body = make_plan_header_body(review_pr=10)

    updated_body = update_plan_header_review_pr(body, 99)

    # Verify the field was overwritten
    assert "review_pr: 99" in updated_body
    assert "review_pr: 10" not in updated_body


def test_update_plan_header_review_pr_preserves_other_fields() -> None:
    """Test that updating review_pr preserves other fields."""
    body = make_plan_header_body(review_pr=None)

    updated_body = update_plan_header_review_pr(body, 123)

    # Verify other fields are preserved
    assert "schema_version: '2'" in updated_body
    assert "created_at: '2025-11-25T14:37:43.513418+00:00'" in updated_body
    assert "created_by: testuser" in updated_body
    assert "plan_comment_id: 123456789" in updated_body


def test_update_plan_header_review_pr_missing_block() -> None:
    """Test error when plan-header block is missing."""
    body = "This is just regular text with no metadata block."

    with pytest.raises(ValueError, match="plan-header block not found"):
        update_plan_header_review_pr(body, 42)


# ============================================================================
# extract_plan_header_review_pr Tests
# ============================================================================


def test_extract_plan_header_review_pr() -> None:
    """Test extracting review_pr field from plan-header."""
    body = make_plan_header_body(review_pr=42)

    result = extract_plan_header_review_pr(body)

    assert result == 42


def test_extract_plan_header_review_pr_not_present() -> None:
    """Test extracting review_pr field when it's null."""
    body = make_plan_header_body(review_pr=None)

    result = extract_plan_header_review_pr(body)

    assert result is None


def test_extract_plan_header_review_pr_missing_block() -> None:
    """Test error when plan-header block is missing."""
    body = "This is just regular text with no metadata block."

    with pytest.raises(ValueError, match="plan-header block not found"):
        extract_plan_header_review_pr(body)


def test_extract_plan_header_review_pr_after_update() -> None:
    """Test extracting review_pr after updating it."""
    body = make_plan_header_body(review_pr=None)

    # Update the field
    updated_body = update_plan_header_review_pr(body, 789)

    # Extract and verify
    result = extract_plan_header_review_pr(updated_body)
    assert result == 789
