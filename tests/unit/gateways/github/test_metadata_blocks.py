"""Tests for GitHub metadata blocks API."""

import logging

import pytest

from erk_shared.github.metadata_blocks import (
    ImplementationStatusSchema,
    MetadataBlock,
    ProgressStatusSchema,
    create_implementation_status_block,
    create_metadata_block,
    create_progress_status_block,
    extract_metadata_value,
    extract_raw_metadata_blocks,
    find_metadata_block,
    parse_metadata_block_body,
    parse_metadata_blocks,
    render_erk_issue_event,
    render_metadata_block,
)

# === Block Creation Tests ===


def test_create_block_without_schema() -> None:
    """Test basic block creation without schema validation."""
    block = create_metadata_block(
        key="test-key",
        data={"field": "value"},
    )
    assert block.key == "test-key"
    assert block.data == {"field": "value"}


def test_create_block_with_valid_schema() -> None:
    """Test block creation with valid schema."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 5,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }
    block = create_metadata_block(
        key="test-status",
        data=data,
        schema=schema,
    )
    assert block.key == "test-status"
    assert block.data == data


def test_create_block_with_invalid_data_raises() -> None:
    """Test block creation with invalid data raises ValueError."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "invalid-status",
        "completed_steps": 3,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="Invalid status 'invalid-status'"):
        create_metadata_block(key="test-key", data=data, schema=schema)


def test_metadata_block_is_immutable() -> None:
    """Test that MetadataBlock is frozen (immutable)."""
    block = MetadataBlock(key="test", data={"field": "value"})
    with pytest.raises(AttributeError):  # FrozenInstanceError is subclass
        block.key = "changed"  # type: ignore


# === Rendering Tests ===


def test_render_basic_block() -> None:
    """Test basic markdown rendering with HTML comment wrappers."""
    block = MetadataBlock(
        key="test-key",
        data={"field": "value", "number": 42},
    )
    rendered = render_metadata_block(block)

    # Verify HTML comment structure
    assert "<!-- WARNING: Machine-generated" in rendered
    assert "<!-- erk:metadata-block:test-key -->" in rendered
    assert "<!-- /erk:metadata-block:test-key -->" in rendered

    # Verify details structure
    assert "<details>" in rendered
    assert "<summary><code>test-key</code></summary>" in rendered
    assert "```yaml" in rendered
    assert "</details>" in rendered

    # Verify blank lines around YAML code fence
    lines = rendered.split("\n")
    summary_idx = next(i for i, line in enumerate(lines) if "</summary>" in line)
    yaml_start_idx = next(i for i, line in enumerate(lines) if "```yaml" in line)
    yaml_end_idx = next(
        i for i, line in enumerate(lines) if line.strip() == "```" and i > yaml_start_idx
    )
    details_end_idx = next(i for i, line in enumerate(lines) if "</details>" in line)

    # Verify blank line after </summary>
    assert lines[summary_idx + 1] == ""
    # Verify blank line after ```yaml
    assert lines[yaml_start_idx + 1] == ""
    # Verify blank line before closing ``` (this is the new format)
    assert lines[yaml_end_idx - 1].strip() == ""
    # Verify blank line after closing ```
    assert lines[yaml_end_idx + 1] == ""
    # Verify blank line before </details>
    assert lines[details_end_idx - 1] == ""

    # Verify round-trip parsing works
    parsed = parse_metadata_blocks(rendered)
    assert len(parsed) == 1
    assert parsed[0].key == "test-key"
    assert parsed[0].data == {"field": "value", "number": 42}


def test_render_details_closed_by_default() -> None:
    """Test that details block is closed by default (no 'open' attribute)."""
    block = MetadataBlock(key="test", data={"field": "value"})
    rendered = render_metadata_block(block)

    assert "<details>" in rendered
    assert "open" not in rendered.lower()


def test_render_no_trailing_newline() -> None:
    """Test that rendered YAML has proper spacing with blank lines."""
    block = MetadataBlock(key="test", data={"field": "value"})
    rendered = render_metadata_block(block)

    # Check that YAML structure has correct blank lines
    lines = rendered.split("\n")
    yaml_start_idx = next(i for i, line in enumerate(lines) if "```yaml" in line)
    yaml_end_idx = next(
        i for i, line in enumerate(lines) if line.strip() == "```" and i > yaml_start_idx
    )

    assert yaml_end_idx is not None
    # Should have blank line after ```yaml
    assert lines[yaml_start_idx + 1].strip() == ""
    # Should have YAML content
    assert lines[yaml_start_idx + 2].strip() == "field: value"
    # Should have blank line before closing ```
    assert lines[yaml_end_idx - 1].strip() == ""


def test_render_special_characters() -> None:
    """Test rendering with special characters in values."""
    block = MetadataBlock(
        key="test-key",
        data={"message": "Line 1\nLine 2", "quote": 'Value with "quotes"'},
    )
    rendered = render_metadata_block(block)

    # YAML should handle special characters correctly
    assert "message:" in rendered
    assert "quote:" in rendered


# === Schema Validation Tests ===


def test_schema_validation_accepts_valid_data() -> None:
    """Test ImplementationStatusSchema accepts valid data with summary."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "in_progress",
        "completed_steps": 3,
        "total_steps": 5,
        "summary": "Making progress",
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise


def test_schema_validation_rejects_missing_fields() -> None:
    """Test schema rejects missing required fields."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 5,
        # Missing total_steps, timestamp
    }

    with pytest.raises(ValueError) as exc_info:
        schema.validate(data)

    error_msg = str(exc_info.value)
    assert "Missing required fields" in error_msg
    assert "timestamp" in error_msg
    assert "total_steps" in error_msg


def test_schema_validation_rejects_invalid_status() -> None:
    """Test schema rejects invalid status values."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "invalid-status",
        "completed_steps": 3,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="Invalid status 'invalid-status'"):
        schema.validate(data)


def test_schema_validation_rejects_non_integer_completed_steps() -> None:
    """Test schema rejects non-integer completed_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": "not-an-int",
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="completed_steps must be an integer"):
        schema.validate(data)


def test_schema_validation_rejects_non_integer_total_steps() -> None:
    """Test schema rejects non-integer total_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 5,
        "total_steps": 5.5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="total_steps must be an integer"):
        schema.validate(data)


def test_schema_validation_rejects_negative_completed_steps() -> None:
    """Test schema rejects negative completed_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": -1,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="completed_steps must be non-negative"):
        schema.validate(data)


def test_schema_validation_rejects_zero_total_steps() -> None:
    """Test schema rejects zero total_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 0,
        "total_steps": 0,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="total_steps must be at least 1"):
        schema.validate(data)


def test_schema_validation_rejects_completed_exceeds_total() -> None:
    """Test schema rejects completed_steps > total_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 10,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="completed_steps cannot exceed total_steps"):
        schema.validate(data)


def test_schema_get_key() -> None:
    """Test schema returns correct key."""
    schema = ImplementationStatusSchema()
    assert schema.get_key() == "erk-implementation-status"


def test_implementation_status_schema_accepts_without_summary() -> None:
    """Test ImplementationStatusSchema accepts data without optional summary."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 5,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise


# === ProgressStatusSchema Tests ===


def test_progress_schema_validates_valid_data() -> None:
    """Test ProgressStatusSchema accepts valid data."""
    schema = ProgressStatusSchema()
    data = {
        "status": "in_progress",
        "completed_steps": 3,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
        "step_description": "Phase 1 complete",
    }
    schema.validate(data)  # Should not raise


def test_progress_schema_validates_without_step_description() -> None:
    """Test ProgressStatusSchema accepts data without optional step_description."""
    schema = ProgressStatusSchema()
    data = {
        "status": "in_progress",
        "completed_steps": 2,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise


def test_progress_schema_rejects_missing_required_field() -> None:
    """Test ProgressStatusSchema rejects missing required fields."""
    schema = ProgressStatusSchema()
    data = {
        "status": "in_progress",
        "completed_steps": 3,
        # missing total_steps
        "timestamp": "2025-11-22T12:00:00Z",
    }
    with pytest.raises(ValueError, match="Missing required fields: total_steps"):
        schema.validate(data)


def test_progress_schema_rejects_invalid_status() -> None:
    """Test ProgressStatusSchema rejects invalid status values."""
    schema = ProgressStatusSchema()
    data = {
        "status": "invalid",
        "completed_steps": 3,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }
    with pytest.raises(ValueError, match="Invalid status"):
        schema.validate(data)


def test_progress_schema_get_key() -> None:
    """Test ProgressStatusSchema returns correct key."""
    schema = ProgressStatusSchema()
    assert schema.get_key() == "erk-implementation-status"


def test_create_progress_status_block_with_description() -> None:
    """Test create_progress_status_block with step_description."""
    block = create_progress_status_block(
        status="in_progress",
        completed_steps=3,
        total_steps=5,
        timestamp="2025-11-22T12:00:00Z",
        step_description="Phase 1 complete",
    )
    assert block.key == "erk-implementation-status"
    assert block.data["status"] == "in_progress"
    assert block.data["completed_steps"] == 3
    assert block.data["step_description"] == "Phase 1 complete"


def test_create_progress_status_block_without_description() -> None:
    """Test create_progress_status_block without step_description."""
    block = create_progress_status_block(
        status="in_progress",
        completed_steps=2,
        total_steps=5,
        timestamp="2025-11-22T12:00:00Z",
    )
    assert block.key == "erk-implementation-status"
    assert "step_description" not in block.data


# === Parsing Tests ===


# Phase 1: Raw Block Extraction Tests


def test_extract_raw_metadata_blocks_single() -> None:
    """Test Phase 1: Extract single raw metadata block."""
    text = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:test-key -->
<details>
<summary><code>test-key</code></summary>
```yaml
field: value
```
</details>
<!-- /erk:metadata-block -->"""

    raw_blocks = extract_raw_metadata_blocks(text)
    assert len(raw_blocks) == 1
    assert raw_blocks[0].key == "test-key"
    assert "<details>" in raw_blocks[0].body
    assert "field: value" in raw_blocks[0].body


def test_extract_raw_metadata_blocks_multiple() -> None:
    """Test Phase 1: Extract multiple raw metadata blocks."""
    text = """Some text here

<!-- erk:metadata-block:block-1 -->
<details>
<summary><code>block-1</code></summary>
```yaml
field: value1
```
</details>
<!-- /erk:metadata-block -->

More text

<!-- erk:metadata-block:block-2 -->
<details>
<summary><code>block-2</code></summary>
```yaml
field: value2
```
</details>
<!-- /erk:metadata-block -->"""

    raw_blocks = extract_raw_metadata_blocks(text)
    assert len(raw_blocks) == 2
    assert raw_blocks[0].key == "block-1"
    assert raw_blocks[1].key == "block-2"
    assert "value1" in raw_blocks[0].body
    assert "value2" in raw_blocks[1].body


def test_extract_raw_metadata_blocks_no_blocks() -> None:
    """Test Phase 1: Extract returns empty list when no blocks present."""
    text = "Just some regular markdown text without metadata blocks"
    raw_blocks = extract_raw_metadata_blocks(text)
    assert raw_blocks == []


# Phase 2: Body Parsing Tests


def test_parse_metadata_block_body_valid() -> None:
    """Test Phase 2: Parse valid metadata block body."""
    body = """<details>
<summary><code>test-key</code></summary>
```yaml
status: complete
count: 42
```
</details>"""

    data = parse_metadata_block_body(body)
    assert data == {"status": "complete", "count": 42}


def test_parse_metadata_block_body_invalid_format() -> None:
    """Test Phase 2: Raise ValueError for invalid body format."""
    body = "Just some text without proper structure"

    with pytest.raises(ValueError, match="does not match expected <details> structure"):
        parse_metadata_block_body(body)


def test_parse_metadata_block_body_invalid_yaml() -> None:
    """Test Phase 2: Raise ValueError for malformed YAML."""
    body = """<details>
<summary><code>test-key</code></summary>
```yaml
invalid: yaml: content:
```
</details>"""

    with pytest.raises(ValueError, match="Failed to parse YAML content"):
        parse_metadata_block_body(body)


def test_parse_metadata_block_body_non_dict_yaml() -> None:
    """Test Phase 2: Raise ValueError when YAML is not a dict."""
    body = """<details>
<summary><code>test-key</code></summary>
```yaml
- list
- item
```
</details>"""

    with pytest.raises(ValueError, match="YAML content is not a dict"):
        parse_metadata_block_body(body)


# Integration: Two-Phase Parsing Tests


def test_parse_metadata_blocks_skips_invalid_bodies(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that parse_metadata_blocks skips blocks with invalid bodies (lenient)."""
    text = """<!-- erk:metadata-block:valid-block -->
<details>
<summary><code>valid-block</code></summary>
```yaml
field: value
```
</details>
<!-- /erk:metadata-block -->

<!-- erk:metadata-block:invalid-block -->
Invalid body structure without proper details tags
<!-- /erk:metadata-block -->"""

    with caplog.at_level(logging.DEBUG):
        blocks = parse_metadata_blocks(text)
    # Should skip invalid block and return only the valid one
    assert len(blocks) == 1
    assert blocks[0].key == "valid-block"
    assert blocks[0].data == {"field": "value"}

    # Should log debug message for invalid block
    assert any(
        "Failed to parse metadata block 'invalid-block'" in record.message
        for record in caplog.records
    )


# Existing Parsing Tests


def test_parse_single_block() -> None:
    """Test parsing a single metadata block with new format."""
    text = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:test-key -->
<details>
<summary><code>test-key</code></summary>
```yaml
field: value
number: 42
```
</details>
<!-- /erk:metadata-block -->"""

    blocks = parse_metadata_blocks(text)
    assert len(blocks) == 1
    assert blocks[0].key == "test-key"
    assert blocks[0].data == {"field": "value", "number": 42}


def test_parse_multiple_blocks() -> None:
    """Test parsing multiple metadata blocks with new format."""
    text = """Some text here

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:block-1 -->
<details>
<summary><code>block-1</code></summary>
```yaml
field: value1
```
</details>
<!-- /erk:metadata-block -->

More text

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:block-2 -->
<details>
<summary><code>block-2</code></summary>
```yaml
field: value2
```
</details>
<!-- /erk:metadata-block -->"""

    blocks = parse_metadata_blocks(text)
    assert len(blocks) == 2
    assert blocks[0].key == "block-1"
    assert blocks[0].data == {"field": "value1"}
    assert blocks[1].key == "block-2"
    assert blocks[1].data == {"field": "value2"}


def test_parse_no_blocks_returns_empty_list() -> None:
    """Test parsing text with no blocks returns empty list."""
    text = "Just some regular markdown text"
    blocks = parse_metadata_blocks(text)
    assert blocks == []


def test_parse_lenient_on_invalid_yaml(caplog: pytest.LogCaptureFixture) -> None:
    """Test parsing returns empty list for malformed YAML (lenient)."""
    text = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:test-key -->
<details>
<summary><code>test-key</code></summary>
```yaml
invalid: yaml: content:
```
</details>
<!-- /erk:metadata-block -->"""

    with caplog.at_level(logging.DEBUG):
        blocks = parse_metadata_blocks(text)
    assert blocks == []
    # Should log debug message
    assert any("Failed to parse YAML" in record.message for record in caplog.records)


def test_parse_lenient_on_non_dict_yaml(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test parsing skips blocks where YAML is not a dict."""
    text = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:test-key -->
<details>
<summary><code>test-key</code></summary>
```yaml
- list
- item
```
</details>
<!-- /erk:metadata-block -->"""

    with caplog.at_level(logging.DEBUG):
        blocks = parse_metadata_blocks(text)
    assert blocks == []
    # Should log debug message
    assert any("YAML content is not a dict" in record.message for record in caplog.records)


def test_find_metadata_block_existing_key() -> None:
    """Test find_metadata_block with existing key."""
    text = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:test-key -->
<details>
<summary><code>test-key</code></summary>
```yaml
field: value
```
</details>
<!-- /erk:metadata-block -->"""

    block = find_metadata_block(text, "test-key")
    assert block is not None
    assert block.key == "test-key"
    assert block.data == {"field": "value"}


def test_find_metadata_block_missing_key() -> None:
    """Test find_metadata_block with missing key returns None."""
    text = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:other-key -->
<details>
<summary><code>other-key</code></summary>
```yaml
field: value
```
</details>
<!-- /erk:metadata-block -->"""

    block = find_metadata_block(text, "test-key")
    assert block is None


def test_extract_metadata_value_existing_field() -> None:
    """Test extract_metadata_value with existing field."""
    text = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:test-key -->
<details>
<summary><code>test-key</code></summary>
```yaml
field: value
number: 42
```
</details>
<!-- /erk:metadata-block -->"""

    value = extract_metadata_value(text, "test-key", "field")
    assert value == "value"

    number = extract_metadata_value(text, "test-key", "number")
    assert number == 42


def test_extract_metadata_value_missing_field() -> None:
    """Test extract_metadata_value with missing field returns None."""
    text = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:test-key -->
<details>
<summary><code>test-key</code></summary>
```yaml
field: value
```
</details>
<!-- /erk:metadata-block -->"""

    value = extract_metadata_value(text, "test-key", "missing")
    assert value is None


def test_extract_metadata_value_missing_block() -> None:
    """Test extract_metadata_value with missing block returns None."""
    text = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:other-key -->
<details>
<summary><code>other-key</code></summary>
```yaml
field: value
```
</details>
<!-- /erk:metadata-block -->"""

    value = extract_metadata_value(text, "test-key", "field")
    assert value is None


# === Integration Tests ===


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


# === render_erk_issue_event Tests ===


def test_render_erk_issue_event_with_all_parameters() -> None:
    """Test render_erk_issue_event with title, metadata, and description."""
    block = create_progress_status_block(
        status="in_progress",
        completed_steps=3,
        total_steps=5,
        timestamp="2025-11-22T12:00:00Z",
        step_description="Phase 1 complete",
    )

    comment = render_erk_issue_event(
        title="✓ Step 3/5 completed",
        metadata=block,
        description="Next: implement feature X",
    )

    # Verify structure
    assert comment.startswith("✓ Step 3/5 completed\n\n")
    assert "<!-- erk:metadata-block:erk-implementation-status -->" in comment
    assert "\n---\n\nNext: implement feature X" in comment

    # Verify format: title -> blank -> metadata -> blank -> separator -> blank -> description
    lines = comment.split("\n")
    assert lines[0] == "✓ Step 3/5 completed"
    assert lines[1] == ""  # Blank line after title
    # Metadata block appears next
    separator_idx = lines.index("---")
    assert lines[separator_idx - 1] == ""  # Blank line before separator
    assert lines[separator_idx + 1] == ""  # Blank line after separator
    assert lines[separator_idx + 2] == "Next: implement feature X"


def test_render_erk_issue_event_with_empty_description() -> None:
    """Test render_erk_issue_event with empty description (optional parameter)."""
    block = create_implementation_status_block(
        status="complete",
        completed_steps=5,
        total_steps=5,
        timestamp="2025-11-22T12:00:00Z",
    )

    comment = render_erk_issue_event(
        title="✅ Implementation complete",
        metadata=block,
        description="",
    )

    # Verify structure: title -> blank -> metadata -> blank -> separator -> blank (no description)
    assert comment.startswith("✅ Implementation complete\n\n")
    assert "<!-- erk:metadata-block:erk-implementation-status -->" in comment
    assert comment.endswith("---\n")

    # Ensure no description text after separator
    lines = comment.split("\n")
    separator_idx = lines.index("---")
    # Last line should be blank (after separator)
    assert len(lines) == separator_idx + 2
    assert lines[-1] == ""


def test_render_erk_issue_event_markdown_structure() -> None:
    """Test render_erk_issue_event produces valid markdown structure."""
    block = create_progress_status_block(
        status="in_progress",
        completed_steps=2,
        total_steps=4,
        timestamp="2025-11-22T12:00:00Z",
    )

    comment = render_erk_issue_event(
        title="Progress Update",
        metadata=block,
        description="Working on implementation",
    )

    # Verify blank lines are preserved for markdown rendering
    lines = comment.split("\n")

    # Title at start
    assert lines[0] == "Progress Update"
    assert lines[1] == ""  # Blank after title

    # Metadata block appears (starts with comment)
    metadata_start = next(i for i, line in enumerate(lines) if "<!-- WARNING:" in line)
    assert lines[metadata_start - 1] == ""  # Blank before metadata

    # Separator exists with blank lines around it
    separator_idx = lines.index("---")
    assert lines[separator_idx - 1] == ""  # Blank before separator
    assert lines[separator_idx + 1] == ""  # Blank after separator

    # Description after separator
    assert lines[separator_idx + 2] == "Working on implementation"


# === Plan Wrapping Tests ===


def test_wrap_simple_plan_format() -> None:
    """Test that plan wrapping produces correct collapsible format."""
    plan_content = "# My Plan\n1. Step one\n2. Step two"

    # Simulate the wrap_plan_in_metadata_block output format
    expected_intro = "This issue contains an implementation plan:"
    wrapped = f"""{expected_intro}

<details>
<summary><code>erk-plan</code></summary>

{plan_content}
</details>"""

    # Verify structure
    assert expected_intro in wrapped
    assert "<details>" in wrapped
    assert "<summary><code>erk-plan</code></summary>" in wrapped
    assert plan_content in wrapped
    assert "</details>" in wrapped

    # Verify block is collapsible (no 'open' attribute)
    assert "open" not in wrapped.lower()


def test_wrap_plan_preserves_formatting() -> None:
    """Test that markdown formatting is preserved in wrapped plan."""
    plan_content = """# Implementation Plan

## Phase 1
- Task 1
- Task 2

## Phase 2
1. Step one
2. Step two"""

    wrapped = f"""This issue contains an implementation plan:

<details>
<summary><code>erk-plan</code></summary>

{plan_content}
</details>"""

    # Verify all formatting elements are preserved
    assert "# Implementation Plan" in wrapped
    assert "## Phase 1" in wrapped
    assert "## Phase 2" in wrapped
    assert "- Task 1" in wrapped
    assert "1. Step one" in wrapped


def test_wrap_plan_with_special_characters() -> None:
    """Test that special characters are handled in wrapped plans."""
    plan_content = """# Plan with Special Characters

- Quotes: "double" and 'single'
- Backticks: `code`
- Symbols: @#$%^&*()
- Unicode: 🔥 ✅ ❌"""

    wrapped = f"""This issue contains an implementation plan:

<details>
<summary><code>erk-plan</code></summary>

{plan_content}
</details>"""

    # Verify special characters are preserved
    assert '"double"' in wrapped
    assert "'single'" in wrapped
    assert "`code`" in wrapped
    assert "@#$%^&*()" in wrapped
    assert "🔥" in wrapped
    assert "✅" in wrapped


def test_rendered_plan_block_is_parseable() -> None:
    """Test that wrapped plan has correct HTML structure."""
    plan_content = "# Test Plan\n1. First step\n2. Second step"

    wrapped = f"""This issue contains an implementation plan:

<details>
<summary><code>erk-plan</code></summary>

{plan_content}
</details>"""

    # Verify structure is correct for GitHub rendering
    assert "<details>" in wrapped
    assert "<summary><code>erk-plan</code></summary>" in wrapped
    assert plan_content in wrapped
    assert "</details>" in wrapped


# === PlanIssueSchema Tests ===


def test_plan_issue_schema_validates_valid_data() -> None:
    """Test PlanIssueSchema accepts valid data."""
    from erk_shared.github.metadata_blocks import PlanIssueSchema

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
    from erk_shared.github.metadata_blocks import PlanIssueSchema

    schema = PlanIssueSchema()
    data = {
        "issue_number": 456,
        "worktree_name": "fix-bug",
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise


def test_plan_issue_schema_rejects_missing_required_field() -> None:
    """Test PlanIssueSchema rejects missing required fields."""
    from erk_shared.github.metadata_blocks import PlanIssueSchema

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
    from erk_shared.github.metadata_blocks import PlanIssueSchema

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
    from erk_shared.github.metadata_blocks import PlanIssueSchema

    schema = PlanIssueSchema()
    assert schema.get_key() == "erk-plan"


# === create_plan_issue_block Tests ===


def test_create_plan_issue_block_with_plan_file() -> None:
    """Test create_plan_issue_block with plan_file."""
    from erk_shared.github.metadata_blocks import create_plan_issue_block

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
    from erk_shared.github.metadata_blocks import create_plan_issue_block

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
    from erk_shared.github.metadata_blocks import (
        create_plan_issue_block,
        render_erk_issue_event,
    )

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


# === format_plan_issue_body_simple Tests ===


def test_format_plan_issue_body_simple_basic() -> None:
    """Test format_plan_issue_body_simple produces correct collapsible format."""
    from erk_shared.github.metadata import format_plan_issue_body_simple

    plan_content = "# My Plan\n1. Step one\n2. Step two"
    result = format_plan_issue_body_simple(plan_content)

    # Verify metadata block wrapper structure
    assert "<!-- WARNING: Machine-generated" in result
    assert "<!-- erk:metadata-block:plan-body -->" in result
    assert "<!-- /erk:metadata-block:plan-body -->" in result

    # Verify collapsible details structure
    assert "<details>" in result
    assert "<summary><strong>📋 Implementation Plan</strong></summary>" in result
    assert "</details>" in result

    # Verify plan content is present
    assert "# My Plan" in result
    assert "1. Step one" in result
    assert "2. Step two" in result


def test_format_plan_issue_body_simple_no_execution_commands() -> None:
    """Test format_plan_issue_body_simple does NOT include execution commands."""
    from erk_shared.github.metadata import format_plan_issue_body_simple

    plan_content = "# Plan Content"
    result = format_plan_issue_body_simple(plan_content)

    # Verify no execution commands section (the key optimization)
    assert "## Execution Commands" not in result
    assert "erk submit" not in result
    assert "erk implement" not in result
    assert "--yolo" not in result
    assert "--dangerous" not in result


def test_format_plan_issue_body_simple_preserves_markdown() -> None:
    """Test that markdown formatting is preserved in simple body."""
    from erk_shared.github.metadata import format_plan_issue_body_simple

    plan_content = """# Implementation Plan

## Phase 1
- Task 1
- Task 2

## Phase 2
1. Step one
2. Step two

```python
def example():
    pass
```"""

    result = format_plan_issue_body_simple(plan_content)

    # Verify all formatting elements are preserved
    assert "# Implementation Plan" in result
    assert "## Phase 1" in result
    assert "## Phase 2" in result
    assert "- Task 1" in result
    assert "1. Step one" in result
    assert "```python" in result
    assert "def example():" in result


# === Block Replacement Tests ===


def test_replace_metadata_block_in_body_simple() -> None:
    """Test replacing a metadata block in body."""
    from erk_shared.github.metadata import replace_metadata_block_in_body

    body = """Some preamble

<!-- erk:metadata-block:test-key -->
<details>
<summary><code>test-key</code></summary>
```yaml
old: value
```
</details>
<!-- /erk:metadata-block:test-key -->

Some suffix"""

    new_block = """<!-- erk:metadata-block:test-key -->
<details>
<summary><code>test-key</code></summary>
```yaml
new: value
```
</details>
<!-- /erk:metadata-block:test-key -->"""

    result = replace_metadata_block_in_body(body, "test-key", new_block)

    assert "Some preamble" in result
    assert "Some suffix" in result
    assert "new: value" in result
    assert "old: value" not in result


def test_replace_metadata_block_in_body_preserves_surrounding_content() -> None:
    """Test that content before and after block is preserved."""
    from erk_shared.github.metadata import replace_metadata_block_in_body

    body = """# Plan Issue

Some description here.

<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>
```yaml
schema_version: '2'
```
</details>
<!-- /erk:metadata-block:plan-header -->

## Implementation Steps

- Step 1
- Step 2"""

    new_block = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>
```yaml
schema_version: '3'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    result = replace_metadata_block_in_body(body, "plan-header", new_block)

    assert "# Plan Issue" in result
    assert "Some description here." in result
    assert "## Implementation Steps" in result
    assert "- Step 1" in result
    assert "- Step 2" in result
    assert "schema_version: '3'" in result
    assert "schema_version: '2'" not in result


def test_replace_metadata_block_not_found_raises() -> None:
    """Test that ValueError is raised when block not found."""
    from erk_shared.github.metadata import replace_metadata_block_in_body

    body = "No metadata blocks here"

    with pytest.raises(ValueError, match="Metadata block 'test-key' not found"):
        replace_metadata_block_in_body(body, "test-key", "new content")


def test_replace_metadata_block_handles_generic_closing_tag() -> None:
    """Test replacing block with generic closing tag (<!-- /erk:metadata-block -->)."""
    from erk_shared.github.metadata import replace_metadata_block_in_body

    body = """<!-- erk:metadata-block:test-key -->
content
<!-- /erk:metadata-block -->"""

    new_block = "NEW BLOCK"
    result = replace_metadata_block_in_body(body, "test-key", new_block)

    assert result == "NEW BLOCK"


# === update_plan_header_dispatch Tests ===


def test_update_plan_header_dispatch_basic() -> None:
    """Test update_plan_header_dispatch updates dispatch fields."""
    from erk_shared.github.metadata import update_plan_header_dispatch

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
    from erk_shared.github.metadata import update_plan_header_dispatch

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
    from erk_shared.github.metadata import update_plan_header_dispatch

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


# === format_plan_content_comment and extract_plan_from_comment Tests ===


def test_format_plan_content_comment_produces_collapsible_block() -> None:
    """Test that format_plan_content_comment uses collapsible metadata block format."""
    from erk_shared.github.metadata import format_plan_content_comment

    plan_content = "# My Plan\n1. Step one\n2. Step two"
    result = format_plan_content_comment(plan_content)

    # Verify metadata block wrapper structure
    assert "<!-- WARNING: Machine-generated" in result
    assert "<!-- erk:metadata-block:plan-body -->" in result
    assert "<!-- /erk:metadata-block:plan-body -->" in result

    # Verify collapsible details structure
    assert "<details>" in result
    assert "<summary><strong>📋 Implementation Plan</strong></summary>" in result
    assert "</details>" in result

    # Verify plan content is present
    assert "# My Plan" in result
    assert "1. Step one" in result
    assert "2. Step two" in result


def test_format_plan_content_comment_strips_whitespace() -> None:
    """Test that format_plan_content_comment strips leading/trailing whitespace."""
    from erk_shared.github.metadata import format_plan_content_comment

    plan_content = "\n\n  # My Plan  \n\n"
    result = format_plan_content_comment(plan_content)

    # The plan content should be stripped
    assert "# My Plan" in result
    # Verify it doesn't have excessive leading whitespace before "# My Plan"
    lines = result.split("\n")
    plan_line_idx = next(i for i, line in enumerate(lines) if "# My Plan" in line)
    assert lines[plan_line_idx].strip() == "# My Plan"


def test_extract_plan_from_comment_new_format() -> None:
    """Test extracting plan from new collapsible metadata block format."""
    from erk_shared.github.metadata import extract_plan_from_comment

    comment_body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-body -->
<details>
<summary><strong>📋 Implementation Plan</strong></summary>

# My Plan
1. Step one
2. Step two

</details>
<!-- /erk:metadata-block:plan-body -->"""

    result = extract_plan_from_comment(comment_body)

    assert result is not None
    assert "# My Plan" in result
    assert "1. Step one" in result
    assert "2. Step two" in result


def test_extract_plan_from_comment_old_format_backward_compatible() -> None:
    """Test extracting plan from old marker format (backward compatibility)."""
    from erk_shared.github.metadata import extract_plan_from_comment

    comment_body = """<!-- erk:plan-content -->

# My Plan
1. Step one
2. Step two

<!-- /erk:plan-content -->"""

    result = extract_plan_from_comment(comment_body)

    assert result is not None
    assert "# My Plan" in result
    assert "1. Step one" in result
    assert "2. Step two" in result


def test_extract_plan_from_comment_returns_none_if_not_found() -> None:
    """Test that extract_plan_from_comment returns None if no plan markers found."""
    from erk_shared.github.metadata import extract_plan_from_comment

    comment_body = "Just some regular comment text without any plan markers."

    result = extract_plan_from_comment(comment_body)

    assert result is None


def test_format_and_extract_plan_round_trip() -> None:
    """Test round-trip: format -> extract should return original plan content."""
    from erk_shared.github.metadata import (
        extract_plan_from_comment,
        format_plan_content_comment,
    )

    original_plan = """# Implementation Plan

## Phase 1
- Task 1
- Task 2

## Phase 2
1. Step one
2. Step two

```python
def example():
    pass
```"""

    # Format the plan
    formatted = format_plan_content_comment(original_plan)

    # Extract it back
    extracted = extract_plan_from_comment(formatted)

    # Should get the original content back (stripped)
    assert extracted is not None
    assert extracted.strip() == original_plan.strip()


def test_extract_plan_prefers_new_format_over_old() -> None:
    """Test that new format is preferred when both formats are present."""
    from erk_shared.github.metadata import extract_plan_from_comment

    # Unlikely scenario: both formats present. New format should win.
    comment_body = """<!-- erk:plan-content -->
Old format content
<!-- /erk:plan-content -->

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-body -->
<details>
<summary><strong>📋 Implementation Plan</strong></summary>

New format content

</details>
<!-- /erk:metadata-block:plan-body -->"""

    result = extract_plan_from_comment(comment_body)

    assert result is not None
    assert "New format content" in result
    assert "Old format content" not in result


# === update_plan_header_local_impl Tests ===


def test_update_plan_header_local_impl_basic() -> None:
    """Test update_plan_header_local_impl updates local impl field."""
    from erk_shared.github.metadata import update_plan_header_local_impl

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
    from erk_shared.github.metadata import update_plan_header_local_impl

    body = "No plan-header block here"

    with pytest.raises(ValueError, match="plan-header block not found"):
        update_plan_header_local_impl(
            issue_body=body,
            local_impl_at="2025-11-28T10:00:00Z",
        )


def test_update_plan_header_local_impl_preserves_other_fields() -> None:
    """Test that update_plan_header_local_impl preserves other fields."""
    from erk_shared.github.metadata import update_plan_header_local_impl

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
