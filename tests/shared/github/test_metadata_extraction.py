"""Unit tests for metadata extraction functions.

Layer 3 (Pure Unit Tests): Tests for metadata extraction logic with zero dependencies.
Tests extraction functions that parse metadata blocks from issue bodies.
"""

import pytest

from erk_shared.github.metadata import (
    extract_plan_header_dispatch_info,
    extract_plan_header_local_impl_at,
    extract_plan_header_remote_impl_at,
    extract_plan_header_worktree_name,
    update_plan_header_remote_impl,
    update_plan_header_worktree_name,
)


def test_extract_plan_header_worktree_name_found() -> None:
    """Extract worktree_name from plan-header block when present."""
    issue_body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
worktree_name: optimize-feature-b-24-01-15
last_dispatched_run_id: null
last_dispatched_at: null
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    result = extract_plan_header_worktree_name(issue_body)
    assert result == "optimize-feature-b-24-01-15"


def test_extract_plan_header_worktree_name_missing_block() -> None:
    """Return None when plan-header block is missing."""
    issue_body = """This is a plain issue body without any metadata blocks."""

    result = extract_plan_header_worktree_name(issue_body)
    assert result is None


def test_extract_plan_header_worktree_name_missing_field() -> None:
    """Return None when worktree_name field is missing from block."""
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    result = extract_plan_header_worktree_name(issue_body)
    assert result is None


def test_extract_plan_header_worktree_name_with_dispatch_info() -> None:
    """Extract worktree_name from block that also has dispatch info."""
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
worktree_name: feature-branch-b-24-01-15
last_dispatched_run_id: '1234567890'
last_dispatched_at: '2024-01-15T11:00:00Z'
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    worktree = extract_plan_header_worktree_name(issue_body)
    run_id, node_id, dispatched_at = extract_plan_header_dispatch_info(issue_body)

    assert worktree == "feature-branch-b-24-01-15"
    assert run_id == "1234567890"
    assert node_id is None  # Not present in this test fixture
    assert dispatched_at == "2024-01-15T11:00:00Z"


def test_extract_plan_header_local_impl_at_found() -> None:
    """Extract last_local_impl_at from plan-header block when present."""
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
worktree_name: feature-branch-b-24-01-15
last_dispatched_run_id: null
last_dispatched_at: null
last_local_impl_at: '2024-01-28T14:30:00Z'
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    result = extract_plan_header_local_impl_at(issue_body)
    assert result == "2024-01-28T14:30:00Z"


def test_extract_plan_header_local_impl_at_null() -> None:
    """Return None when last_local_impl_at is explicitly null."""
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
worktree_name: feature-branch-b-24-01-15
last_dispatched_run_id: null
last_dispatched_at: null
last_local_impl_at: null
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    result = extract_plan_header_local_impl_at(issue_body)
    assert result is None


def test_extract_plan_header_local_impl_at_missing() -> None:
    """Return None when last_local_impl_at field is missing."""
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
worktree_name: feature-branch-b-24-01-15
last_dispatched_run_id: null
last_dispatched_at: null
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    result = extract_plan_header_local_impl_at(issue_body)
    assert result is None


def test_extract_plan_header_local_impl_at_missing_block() -> None:
    """Return None when plan-header block is missing."""
    issue_body = """This is a plain issue body without any metadata blocks."""

    result = extract_plan_header_local_impl_at(issue_body)
    assert result is None


def test_update_plan_header_worktree_name_success() -> None:
    """Test updating worktree_name in plan-header block without existing worktree_name."""
    issue_body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
last_dispatched_run_id: null
last_dispatched_at: null
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    updated_body = update_plan_header_worktree_name(issue_body, "my-feature-25-11-28")

    # Verify the worktree_name was added
    worktree_name = extract_plan_header_worktree_name(updated_body)
    assert worktree_name == "my-feature-25-11-28"


def test_update_plan_header_worktree_name_replaces_existing() -> None:
    """Test updating worktree_name replaces existing value."""
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
worktree_name: old-name-24-01-15
last_dispatched_run_id: null
last_dispatched_at: null
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    updated_body = update_plan_header_worktree_name(issue_body, "new-name-25-11-28")

    # Verify the worktree_name was replaced
    worktree_name = extract_plan_header_worktree_name(updated_body)
    assert worktree_name == "new-name-25-11-28"


def test_update_plan_header_worktree_name_no_block_raises() -> None:
    """Test error when plan-header block not found."""
    issue_body = """This is a plain issue body without any metadata blocks."""

    with pytest.raises(ValueError, match="plan-header block not found"):
        update_plan_header_worktree_name(issue_body, "my-feature-25-11-28")


def test_update_plan_header_worktree_name_preserves_other_fields() -> None:
    """Test that updating worktree_name preserves other fields."""
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
last_dispatched_run_id: '1234567890'
last_dispatched_at: '2024-01-15T11:00:00Z'
last_local_impl_at: '2024-01-15T12:00:00Z'
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    updated_body = update_plan_header_worktree_name(issue_body, "my-feature-25-11-28")

    # Verify the worktree_name was added
    worktree_name = extract_plan_header_worktree_name(updated_body)
    assert worktree_name == "my-feature-25-11-28"

    # Verify other fields are preserved
    run_id, node_id, dispatched_at = extract_plan_header_dispatch_info(updated_body)
    assert run_id == "1234567890"
    assert node_id is None  # Not present in this test fixture
    assert dispatched_at == "2024-01-15T11:00:00Z"

    local_impl_at = extract_plan_header_local_impl_at(updated_body)
    assert local_impl_at == "2024-01-15T12:00:00Z"


# === Remote Impl At Extraction Tests ===


def test_extract_plan_header_remote_impl_at_found() -> None:
    """Extract last_remote_impl_at from plan-header block when present."""
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
worktree_name: feature-branch-b-24-01-15
last_dispatched_run_id: null
last_dispatched_at: null
last_local_impl_at: null
last_remote_impl_at: '2024-01-28T14:30:00Z'
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    result = extract_plan_header_remote_impl_at(issue_body)
    assert result == "2024-01-28T14:30:00Z"


def test_extract_plan_header_remote_impl_at_null() -> None:
    """Return None when last_remote_impl_at is explicitly null."""
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
worktree_name: feature-branch-b-24-01-15
last_dispatched_run_id: null
last_dispatched_at: null
last_local_impl_at: null
last_remote_impl_at: null
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    result = extract_plan_header_remote_impl_at(issue_body)
    assert result is None


def test_extract_plan_header_remote_impl_at_missing() -> None:
    """Return None when last_remote_impl_at field is missing."""
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
worktree_name: feature-branch-b-24-01-15
last_dispatched_run_id: null
last_dispatched_at: null
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    result = extract_plan_header_remote_impl_at(issue_body)
    assert result is None


def test_extract_plan_header_remote_impl_at_missing_block() -> None:
    """Return None when plan-header block is missing."""
    issue_body = """This is a plain issue body without any metadata blocks."""

    result = extract_plan_header_remote_impl_at(issue_body)
    assert result is None


# === Remote Impl At Update Tests ===


def test_update_plan_header_remote_impl_basic() -> None:
    """Test update_plan_header_remote_impl updates remote impl field."""
    issue_body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
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
last_remote_impl_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Plan Content"""

    result = update_plan_header_remote_impl(
        issue_body=issue_body,
        remote_impl_at="2025-11-28T10:00:00Z",
    )

    # Should preserve surrounding content
    assert "# Plan Content" in result

    # Should have updated remote impl field
    remote_impl_at = extract_plan_header_remote_impl_at(result)
    assert remote_impl_at == "2025-11-28T10:00:00Z"


def test_update_plan_header_remote_impl_no_block_raises() -> None:
    """Test update_plan_header_remote_impl raises when no plan-header block."""
    issue_body = "No plan-header block here"

    with pytest.raises(ValueError, match="plan-header block not found"):
        update_plan_header_remote_impl(
            issue_body=issue_body,
            remote_impl_at="2025-11-28T10:00:00Z",
        )


def test_update_plan_header_remote_impl_preserves_other_fields() -> None:
    """Test that update_plan_header_remote_impl preserves other fields."""
    issue_body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
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
last_local_impl_at: '2025-11-27T09:00:00Z'
last_remote_impl_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    result = update_plan_header_remote_impl(
        issue_body=issue_body,
        remote_impl_at="2025-11-28T10:00:00Z",
    )

    # Should preserve dispatch fields
    run_id, node_id, dispatched_at = extract_plan_header_dispatch_info(result)
    assert run_id == "12345"
    assert node_id is None  # Not present in this test fixture
    assert dispatched_at == "2025-11-26T08:00:00Z"

    # Should preserve local impl timestamp
    local_impl_at = extract_plan_header_local_impl_at(result)
    assert local_impl_at == "2025-11-27T09:00:00Z"

    # Should have the new remote impl timestamp
    remote_impl_at = extract_plan_header_remote_impl_at(result)
    assert remote_impl_at == "2025-11-28T10:00:00Z"
