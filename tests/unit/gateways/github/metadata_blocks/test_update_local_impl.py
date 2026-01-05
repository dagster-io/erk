"""Tests for update_plan_header_local_impl function."""

import pytest

from erk_shared.github.metadata import update_plan_header_local_impl


def test_update_plan_header_local_impl_basic() -> None:
    """Test update_plan_header_local_impl updates local impl field."""
    body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-11-25T14:37:43.513418+00:00'
created_by: testuser
worktree_name: test-worktree
last_dispatched_run_id: null
last_dispatched_at: null
last_local_impl_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Plan Content"""

    result = update_plan_header_local_impl(
        issue_body=body,
        local_impl_at="2025-11-28T10:00:00Z",
    )

    # Should preserve surrounding content
    assert "# Plan Content" in result

    # Should have updated local impl field (YAML may or may not quote values)
    has_timestamp = (
        "last_local_impl_at: '2025-11-28T10:00:00Z'" in result
        or "last_local_impl_at: 2025-11-28T10:00:00Z" in result
    )
    assert has_timestamp


def test_update_plan_header_local_impl_no_block_raises() -> None:
    """Test update_plan_header_local_impl raises when no plan-header block."""
    body = "No plan-header block here"

    with pytest.raises(ValueError, match="plan-header block not found"):
        update_plan_header_local_impl(
            issue_body=body,
            local_impl_at="2025-11-28T10:00:00Z",
        )


def test_update_plan_header_local_impl_preserves_other_fields() -> None:
    """Test that update_plan_header_local_impl preserves other fields."""
    body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-11-25T14:37:43.513418+00:00'
created_by: testuser
worktree_name: test-worktree
last_dispatched_run_id: '12345'
last_dispatched_at: '2025-11-26T08:00:00Z'
last_local_impl_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    result = update_plan_header_local_impl(
        issue_body=body,
        local_impl_at="2025-11-28T10:00:00Z",
    )

    # Should preserve dispatch fields
    has_dispatch_run_id = (
        "last_dispatched_run_id: '12345'" in result or "last_dispatched_run_id: 12345" in result
    )
    has_dispatch_at = (
        "last_dispatched_at: '2025-11-26T08:00:00Z'" in result
        or "last_dispatched_at: 2025-11-26T08:00:00Z" in result
    )
    assert has_dispatch_run_id
    assert has_dispatch_at

    # Should have the new local impl timestamp
    has_local_impl = (
        "last_local_impl_at: '2025-11-28T10:00:00Z'" in result
        or "last_local_impl_at: 2025-11-28T10:00:00Z" in result
    )
    assert has_local_impl
