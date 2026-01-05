"""Integration tests for metadata blocks."""

import pytest

from erk_shared.github.metadata_blocks import (
    create_implementation_status_block,
    create_metadata_block,
    extract_metadata_value,
    find_metadata_block,
    parse_metadata_blocks,
    render_metadata_block,
)


def test_round_trip_create_render_parse() -> None:
    """Test round-trip: create -> render -> parse -> extract."""
    # Create
    block = create_metadata_block(
        key="test-key",
        data={"field": "value", "number": 42},
    )

    # Render
    rendered = render_metadata_block(block)

    # Parse
    parsed_blocks = parse_metadata_blocks(rendered)
    assert len(parsed_blocks) == 1
    parsed_block = parsed_blocks[0]

    # Extract
    assert parsed_block.key == "test-key"
    assert parsed_block.data == {"field": "value", "number": 42}

    value = extract_metadata_value(rendered, "test-key", "field")
    assert value == "value"


def test_convenience_function_create_implementation_status_block() -> None:
    """Test create_implementation_status_block convenience function."""
    block = create_implementation_status_block(
        status="in_progress",
        completed_steps=3,
        total_steps=5,
        timestamp="2025-11-22T12:00:00Z",
        summary="Making progress",
    )

    assert block.key == "erk-implementation-status"
    assert block.data["status"] == "in_progress"
    assert block.data["completed_steps"] == 3
    assert block.data["total_steps"] == 5
    assert block.data["summary"] == "Making progress"
    assert block.data["timestamp"] == "2025-11-22T12:00:00Z"


def test_convenience_function_create_implementation_status_block_without_summary() -> None:
    """Test create_implementation_status_block without optional summary."""
    block = create_implementation_status_block(
        status="complete",
        completed_steps=5,
        total_steps=5,
        timestamp="2025-11-22T12:00:00Z",
    )

    assert block.key == "erk-implementation-status"
    assert block.data["status"] == "complete"
    assert "summary" not in block.data


def test_convenience_function_validates_data() -> None:
    """Test convenience function validates data."""
    with pytest.raises(ValueError, match="Invalid status"):
        create_implementation_status_block(
            status="bad-status",
            completed_steps=3,
            total_steps=5,
            timestamp="2025-11-22T12:00:00Z",
            summary="Test",
        )


def test_real_world_github_comment_format() -> None:
    """Test parsing a real-world GitHub comment with metadata block."""
    comment = """## Implementation Progress

We're making good progress on this feature!

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:erk-implementation-status -->
<details>
<summary><code>erk-implementation-status</code></summary>
```yaml
status: in_progress
completed_steps: 3
total_steps: 5
summary: Core functionality implemented
timestamp: '2025-11-22T12:00:00Z'
```
</details>
<!-- /erk:metadata-block -->

Next steps:
- Add tests
- Update documentation
"""

    # Parse block
    block = find_metadata_block(comment, "erk-implementation-status")
    assert block is not None
    assert block.data["status"] == "in_progress"
    assert block.data["completed_steps"] == 3
    assert block.data["total_steps"] == 5

    # Extract values
    status = extract_metadata_value(comment, "erk-implementation-status", "status")
    assert status == "in_progress"

    completed = extract_metadata_value(comment, "erk-implementation-status", "completed_steps")
    assert completed == 3
