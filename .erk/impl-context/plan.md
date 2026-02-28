# Plan: Harden Metadata Block System — Phase 2

**Objective:** #8423 — Harden Metadata Block System
**Nodes:** 2.1, 2.2, 2.3

## Context

Phase 1 (PR #8425) eliminated the duplicate `metadata_blocks.py`, extracted helpers, fixed API usage, and added `MetadataParseResult` for explicit error reporting. Phase 2 completes the hardening by making the system self-describing: a central registry maps all 13 block keys to their category and schema, the parser uses this registry to handle content blocks correctly (instead of reporting them as errors), and parameterized round-trip tests verify every registered block type.

### Problem

Currently `parse_metadata_blocks()` treats all blocks uniformly — it attempts YAML parsing on every raw block. Content blocks (`plan-body`, `objective-body`, `planning-session-prompts`) fail YAML parsing and are collected as `MetadataBlockError`s. This is misleading: these aren't errors, they're intentionally non-YAML blocks. There's also no single place that enumerates all known block types, making it easy for new blocks to be added without proper categorization.

## Node 2.1: Create BlockTypeRegistry

### New file: `packages/erk-shared/src/erk_shared/gateway/github/metadata/registry.py`

Define a `BlockCategory` enum and `BlockTypeInfo` frozen dataclass:

```python
from enum import Enum

class BlockCategory(Enum):
    YAML = "yaml"
    CONTENT = "content"

@dataclass(frozen=True)
class BlockTypeInfo:
    key: str
    category: BlockCategory
    schema: MetadataBlockSchema | None
```

Create the registry as a module-level `dict[str, BlockTypeInfo]` populated at import time, mapping all 13 block keys:

**YAML blocks (10)** — parseable by `parse_metadata_block_body()`:
| Key | Schema Class |
|-----|-------------|
| `plan-header` | `PlanHeaderSchema` |
| `erk-plan` | `PlanSchema` |
| `erk-implementation-status` | `ImplementationStatusSchema` |
| `erk-worktree-creation` | `WorktreeCreationSchema` |
| `submission-queued` | `SubmissionQueuedSchema` |
| `workflow-started` | `WorkflowStartedSchema` |
| `plan-retry` | `PlanRetrySchema` |
| `objective-header` | `ObjectiveHeaderSchema` |
| `tripwire-candidates` | `None` (no schema) |
| `objective-roadmap` | `None` (validated separately via `validate_roadmap_frontmatter`) |

**CONTENT blocks (3)** — custom rendering, not standard YAML:
| Key | Notes |
|-----|-------|
| `plan-body` | Collapsible markdown, `<details open>` + `<strong>` summary |
| `objective-body` | Collapsible markdown, `<details open>` + `<strong>` summary |
| `planning-session-prompts` | Numbered markdown blocks, not YAML |

Public API:
- `get_block_type(key: str) -> BlockTypeInfo | None`
- `get_all_block_types() -> dict[str, BlockTypeInfo]`
- `get_yaml_block_types() -> list[BlockTypeInfo]` (convenience filter)
- `get_content_block_types() -> list[BlockTypeInfo]` (convenience filter)

### Files to modify
- **New:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/registry.py`

## Node 2.2: Make parse_metadata_blocks category-aware

### Modify `MetadataParseResult` in `types.py`

Add a `content_blocks` field:

```python
@dataclass(frozen=True)
class MetadataParseResult:
    blocks: tuple[MetadataBlock, ...]
    content_blocks: tuple[RawMetadataBlock, ...]  # NEW
    errors: tuple[MetadataBlockError, ...]
```

### Modify `parse_metadata_blocks()` in `core.py`

In the Phase 2 loop, before attempting `parse_metadata_block_body()`:
1. Look up the block key in the registry via `get_block_type(raw_block.key)`
2. If category is `CONTENT`, append to `content_blocks` list and skip YAML parsing
3. If category is `YAML` or key is unknown, proceed with YAML parsing as before

Unknown keys (not in registry) still attempt YAML parsing — this preserves backward compatibility and allows parsing of ad-hoc blocks.

### Files to modify
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/types.py` — add `content_blocks` field
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py` — import registry, add category check in `parse_metadata_blocks()`

## Node 2.3: Parameterized round-trip tests

### New file: `tests/unit/gateways/github/metadata_blocks/test_round_trip_all_types.py`

Use `@pytest.mark.parametrize` to test every registered block type.

**YAML block round-trip tests** — one parametrized test covering all 10 YAML blocks:
```python
@pytest.mark.parametrize("key,sample_data", [
    ("plan-header", {"schema_version": "2", "created_at": "2025-01-01T00:00:00Z", "created_by": "test"}),
    ("erk-plan", {"plan_number": 1, "worktree_name": "test-wt", "timestamp": "2025-01-01T00:00:00Z"}),
    # ... all 10 YAML block types with minimal valid data
])
def test_yaml_block_round_trip(key: str, sample_data: dict[str, Any]) -> None:
    block = create_metadata_block(key=key, data=sample_data, schema=None)
    rendered = render_metadata_block(block)
    result = parse_metadata_blocks(rendered)
    assert len(result.blocks) == 1
    assert result.blocks[0].key == key
    assert result.blocks[0].data == sample_data
    assert not result.has_errors
    assert len(result.content_blocks) == 0
```

**YAML block schema validation round-trip** — verify that blocks created with schemas survive round-trip:
```python
@pytest.mark.parametrize("key,sample_data", [...])
def test_yaml_block_schema_round_trip(key: str, sample_data: dict[str, Any]) -> None:
    block_type = get_block_type(key)
    assert block_type is not None
    if block_type.schema is not None:
        block = create_metadata_block(key=key, data=sample_data, schema=block_type.schema)
    else:
        block = create_metadata_block(key=key, data=sample_data, schema=None)
    rendered = render_metadata_block(block)
    result = parse_metadata_blocks(rendered)
    assert result.blocks[0].data == sample_data
```

**Content block category test** — verify content blocks are routed correctly:
```python
@pytest.mark.parametrize("key,render_fn", [
    ("plan-body", lambda: render_plan_body_block(MetadataBlock(key="plan-body", data={"content": "# Plan"}))),
    ("objective-body", lambda: render_objective_body_block("# Objective content")),
    ("planning-session-prompts", lambda: render_session_prompts_block(["prompt 1"], max_prompt_display_length=500)),
])
def test_content_block_not_in_errors(key: str, render_fn: Callable[[], str]) -> None:
    rendered = render_fn()
    result = parse_metadata_blocks(rendered)
    assert len(result.errors) == 0
    assert any(b.key == key for b in result.content_blocks)
```

**Registry completeness test** — verify all 13 block types are registered:
```python
def test_registry_has_all_block_types() -> None:
    all_types = get_all_block_types()
    assert len(all_types) == 13
    yaml_types = get_yaml_block_types()
    content_types = get_content_block_types()
    assert len(yaml_types) == 10
    assert len(content_types) == 3
```

### Files to modify
- **New:** `tests/unit/gateways/github/metadata_blocks/test_round_trip_all_types.py`
- Existing tests in `test_integration.py` and `test_parsing.py` may need minor updates to account for the new `content_blocks` field on `MetadataParseResult`

### Update existing tests

Several existing tests reference `MetadataParseResult` and need to account for the new `content_blocks` field. These tests construct or assert on the result but access fields by name, so they won't break — however some assertions may need updating:

- `test_parsing.py` — tests that verify `len(result.errors)` for content blocks should be updated (those are now `content_blocks`, not errors)
- `test_integration.py` — `test_round_trip_create_render_parse` should verify `result.content_blocks` is empty for YAML blocks

### Callers of `MetadataParseResult` (verified safe)

`MetadataParseResult` is constructed in exactly one place (`core.py:589`). All callers access fields by name (`result.blocks`, `result.errors`), never by position. Callers:
- `core.py:606` (`find_metadata_block`) — iterates `result.blocks`, unaffected
- `status_history.py:34,85` — iterates `result.blocks`, unaffected
- `log_cmd.py:184` — iterates `result.blocks`, unaffected
- Test files — access by name, safe

## Verification

1. Run metadata block tests: `uv run pytest tests/unit/gateways/github/metadata_blocks/ -v`
2. Run broader tests that use `parse_metadata_blocks`: `uv run pytest tests/core/test_impl_folder.py tests/unit/cli/commands/exec/scripts/test_post_workflow_started_comment.py -v`
3. Run type checker on modified package
4. Run linter on modified package
