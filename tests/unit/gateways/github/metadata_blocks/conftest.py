"""Shared fixtures for metadata blocks tests."""

import pytest

from erk_shared.gateway.github.metadata_blocks import MetadataBlock


@pytest.fixture
def sample_block() -> MetadataBlock:
    """Create a sample MetadataBlock for testing."""
    return MetadataBlock(key="test-key", data={"field": "value", "number": 42})


@pytest.fixture
def sample_rendered_block() -> str:
    """Return a sample rendered metadata block."""
    return """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:test-key -->
<details>
<summary><code>test-key</code></summary>
```yaml
field: value
number: 42
```
</details>
<!-- /erk:metadata-block -->"""
