"""Tests for metadata block replacement in body."""

import pytest

from erk_shared.github.metadata.core import replace_metadata_block_in_body


def test_replace_metadata_block_in_body_simple() -> None:
    """Test replacing a metadata block in body."""
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
    body = "No metadata blocks here"

    with pytest.raises(ValueError, match="Metadata block 'test-key' not found"):
        replace_metadata_block_in_body(body, "test-key", "new content")


def test_replace_metadata_block_handles_generic_closing_tag() -> None:
    """Test replacing block with generic closing tag (<!-- /erk:metadata-block -->)."""
    body = """<!-- erk:metadata-block:test-key -->
content
<!-- /erk:metadata-block -->"""

    new_block = "NEW BLOCK"
    result = replace_metadata_block_in_body(body, "test-key", new_block)

    assert result == "NEW BLOCK"
