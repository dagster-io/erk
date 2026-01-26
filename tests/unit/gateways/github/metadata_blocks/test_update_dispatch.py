"""Tests for update_plan_header_dispatch function."""

import pytest

from erk_shared.gateway.github.metadata.plan_header import update_plan_header_dispatch


def test_update_plan_header_dispatch_basic() -> None:
    """Test update_plan_header_dispatch updates dispatch fields."""
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

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Plan Content"""

    result = update_plan_header_dispatch(
        issue_body=body,
        run_id="12345678",
        node_id="WFR_kwLOPxC3hc8AAAAEnZK8rQ",
        dispatched_at="2025-11-25T15:00:00Z",
    )

    # Should preserve surrounding content
    assert "# Plan Content" in result

    # Should have updated dispatch fields (YAML may or may not quote values)
    has_run_id = (
        "last_dispatched_run_id: '12345678'" in result
        or "last_dispatched_run_id: 12345678" in result
    )
    has_node_id = (
        "last_dispatched_node_id: 'WFR_kwLOPxC3hc8AAAAEnZK8rQ'" in result
        or "last_dispatched_node_id: WFR_kwLOPxC3hc8AAAAEnZK8rQ" in result
    )
    has_timestamp = (
        "last_dispatched_at: '2025-11-25T15:00:00Z'" in result
        or "last_dispatched_at: 2025-11-25T15:00:00Z" in result
    )
    assert has_run_id
    assert has_node_id
    assert has_timestamp


def test_update_plan_header_dispatch_no_block_raises() -> None:
    """Test update_plan_header_dispatch raises when no plan-header block."""
    body = "No plan-header block here"

    with pytest.raises(ValueError, match="plan-header block not found"):
        update_plan_header_dispatch(
            issue_body=body,
            run_id="12345678",
            node_id="WFR_kwLOPxC3hc8AAAAEnZK8rQ",
            dispatched_at="2025-11-25T15:00:00Z",
        )


def test_update_plan_header_dispatch_returns_full_body() -> None:
    """Test that update_plan_header_dispatch returns full body, not just block."""
    body = """Preamble content

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
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

```

</details>
<!-- /erk:metadata-block:plan-header -->

Suffix content"""

    result = update_plan_header_dispatch(
        issue_body=body,
        run_id="run-123",
        node_id="WFR_kwLOPxC3hc8AAAAEnZK8rQ",
        dispatched_at="2025-11-25T16:00:00Z",
    )

    # Should have both preamble and suffix
    assert "Preamble content" in result
    assert "Suffix content" in result
    # Should have the updated block
    assert "plan-header" in result
