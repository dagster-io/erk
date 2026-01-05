"""Tests for metadata block parsing."""

import logging

import pytest

from erk_shared.github.metadata_blocks import (
    extract_metadata_value,
    extract_raw_metadata_blocks,
    find_metadata_block,
    parse_metadata_block_body,
    parse_metadata_blocks,
)


# === Phase 1: Raw Block Extraction Tests ===


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


# === Phase 2: Body Parsing Tests ===


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


# === Integration: Two-Phase Parsing Tests ===


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


# === Existing Parsing Tests ===


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
