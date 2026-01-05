"""Tests for metadata block rendering."""

from erk_shared.github.metadata_blocks import (
    MetadataBlock,
    parse_metadata_blocks,
    render_metadata_block,
)


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
