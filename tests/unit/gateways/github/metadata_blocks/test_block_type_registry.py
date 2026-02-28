"""Tests for block type registry and category-aware parsing."""

import pytest

from erk_shared.gateway.github.metadata.core import parse_metadata_blocks, render_metadata_block
from erk_shared.gateway.github.metadata.registry import (
    BlockCategory,
    get_all_block_types,
    get_block_type,
    get_content_block_types,
    get_yaml_block_types,
)
from erk_shared.gateway.github.metadata.types import MetadataBlock

# === Registry Completeness Tests ===


def test_registry_has_all_yaml_schema_block_types() -> None:
    """All block types with MetadataBlockSchema classes are registered."""
    schema_keys = {
        "plan-header",
        "objective-header",
        "erk-plan",
        "erk-worktree-creation",
        "erk-implementation-status",
        "workflow-started",
        "submission-queued",
        "plan-retry",
    }
    all_types = get_all_block_types()
    for key in schema_keys:
        assert key in all_types, f"Missing registry entry for schema block: {key}"
        info = all_types[key]
        assert info.category == BlockCategory.YAML
        assert info.schema is not None, f"Schema block {key} should have a schema"


def test_registry_has_all_content_block_types() -> None:
    """All content block types are registered."""
    content_keys = {"plan-body", "objective-body", "planning-session-prompts"}
    all_types = get_all_block_types()
    for key in content_keys:
        assert key in all_types, f"Missing registry entry for content block: {key}"
        info = all_types[key]
        assert info.category == BlockCategory.CONTENT
        assert info.schema is None, f"Content block {key} should not have a schema"


def test_registry_has_schemaless_yaml_blocks() -> None:
    """YAML blocks without dedicated schemas are registered."""
    schemaless_yaml_keys = {
        "impl-started",
        "impl-ended",
        "learn-invoked",
        "tripwire-candidates",
        "objective-roadmap",
    }
    all_types = get_all_block_types()
    for key in schemaless_yaml_keys:
        assert key in all_types, f"Missing registry entry for schemaless YAML block: {key}"
        info = all_types[key]
        assert info.category == BlockCategory.YAML
        assert info.schema is None


# === Category Filtering Tests ===


def test_get_yaml_block_types_returns_only_yaml() -> None:
    """get_yaml_block_types returns only YAML-category blocks."""
    yaml_types = get_yaml_block_types()
    assert len(yaml_types) > 0
    for info in yaml_types:
        assert info.category == BlockCategory.YAML


def test_get_content_block_types_returns_only_content() -> None:
    """get_content_block_types returns only CONTENT-category blocks."""
    content_types = get_content_block_types()
    assert len(content_types) == 3
    for info in content_types:
        assert info.category == BlockCategory.CONTENT


def test_yaml_and_content_cover_all_types() -> None:
    """YAML + CONTENT types cover the entire registry."""
    all_types = get_all_block_types()
    yaml_keys = {info.key for info in get_yaml_block_types()}
    content_keys = {info.key for info in get_content_block_types()}
    assert yaml_keys | content_keys == set(all_types.keys())
    assert yaml_keys & content_keys == set()


# === Lookup Tests ===


def test_get_block_type_known_key() -> None:
    """get_block_type returns info for known keys."""
    info = get_block_type("plan-header")
    assert info is not None
    assert info.key == "plan-header"
    assert info.category == BlockCategory.YAML


def test_get_block_type_unknown_key() -> None:
    """get_block_type returns None for unknown keys."""
    info = get_block_type("nonexistent-block")
    assert info is None


def test_get_all_block_types_returns_copy() -> None:
    """get_all_block_types returns a copy, not the internal dict."""
    types1 = get_all_block_types()
    types2 = get_all_block_types()
    assert types1 == types2
    assert types1 is not types2


# === BlockTypeInfo Key Consistency ===


def test_registry_keys_match_info_keys() -> None:
    """Registry dict keys match BlockTypeInfo.key for all entries."""
    all_types = get_all_block_types()
    for dict_key, info in all_types.items():
        assert dict_key == info.key, f"Dict key '{dict_key}' != info.key '{info.key}'"


# === Schema Key Consistency ===


@pytest.mark.parametrize(
    "key",
    [
        "plan-header",
        "objective-header",
        "erk-plan",
        "erk-worktree-creation",
        "erk-implementation-status",
        "workflow-started",
        "submission-queued",
        "plan-retry",
    ],
)
def test_schema_get_key_matches_registry_key(key: str) -> None:
    """Schema.get_key() matches the registry key for all schema-backed blocks."""
    info = get_block_type(key)
    assert info is not None
    assert info.schema is not None
    assert info.schema.get_key() == key


# === Parse Routing Tests ===


def test_content_block_not_in_errors() -> None:
    """Content blocks should not appear in parse errors."""
    text = """<!-- erk:metadata-block:plan-body -->
<details open>
<summary><strong>Implementation Plan</strong></summary>

# My Plan

Some markdown content here.

</details>
<!-- /erk:metadata-block:plan-body -->"""

    result = parse_metadata_blocks(text)
    assert len(result.errors) == 0
    assert len(result.content_blocks) == 1
    assert result.content_blocks[0].key == "plan-body"
    assert "My Plan" in result.content_blocks[0].body


def test_content_block_not_in_parsed_blocks() -> None:
    """Content blocks should not appear in parsed YAML blocks."""
    text = """<!-- erk:metadata-block:objective-body -->
<details open>
<summary><strong>Objective</strong></summary>

Some objective content.

</details>
<!-- /erk:metadata-block:objective-body -->"""

    result = parse_metadata_blocks(text)
    assert len(result.blocks) == 0
    assert len(result.content_blocks) == 1
    assert result.content_blocks[0].key == "objective-body"


def test_mixed_yaml_and_content_blocks() -> None:
    """YAML blocks parse as blocks, content blocks go to content_blocks."""
    yaml_block = MetadataBlock(
        key="erk-implementation-status",
        data={"status": "complete", "timestamp": "2024-01-01T00:00:00Z"},
    )
    yaml_rendered = render_metadata_block(yaml_block)

    text = f"""{yaml_rendered}

<!-- erk:metadata-block:plan-body -->
<details open>
<summary><strong>Implementation Plan</strong></summary>

# Plan Content

</details>
<!-- /erk:metadata-block:plan-body -->"""

    result = parse_metadata_blocks(text)
    assert len(result.blocks) == 1
    assert result.blocks[0].key == "erk-implementation-status"
    assert result.blocks[0].data["status"] == "complete"

    assert len(result.content_blocks) == 1
    assert result.content_blocks[0].key == "plan-body"

    assert len(result.errors) == 0


def test_unknown_block_type_still_attempts_yaml_parse() -> None:
    """Unknown block types are still YAML-parsed (backward compat)."""
    text = """<!-- erk:metadata-block:future-block-type -->
<details>
<summary><code>future-block-type</code></summary>

```yaml
field: value
```

</details>
<!-- /erk:metadata-block:future-block-type -->"""

    result = parse_metadata_blocks(text)
    assert len(result.blocks) == 1
    assert result.blocks[0].key == "future-block-type"
    assert result.blocks[0].data == {"field": "value"}
    assert len(result.content_blocks) == 0


def test_unknown_block_type_with_invalid_yaml_becomes_error() -> None:
    """Unknown block types that fail YAML parse become errors."""
    text = """<!-- erk:metadata-block:unknown-type -->
Not valid YAML structure at all
<!-- /erk:metadata-block:unknown-type -->"""

    result = parse_metadata_blocks(text)
    assert len(result.blocks) == 0
    assert len(result.errors) == 1
    assert result.errors[0].key == "unknown-type"


def test_planning_session_prompts_routed_as_content() -> None:
    """planning-session-prompts is a content block, not YAML."""
    text = """<!-- erk:metadata-block:planning-session-prompts -->
<details>
<summary>Planning Session</summary>

**1.** User asked about authentication

**2.** User clarified OAuth requirement

</details>
<!-- /erk:metadata-block:planning-session-prompts -->"""

    result = parse_metadata_blocks(text)
    assert len(result.blocks) == 0
    assert len(result.errors) == 0
    assert len(result.content_blocks) == 1
    assert result.content_blocks[0].key == "planning-session-prompts"
