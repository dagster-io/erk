# Plan: Parameterized Round-Trip Tests for Metadata Block Types

**Objective:** #8423 — Harden Metadata Block System, Node 2.3 (`round-trip-tests`)

## Context

The metadata block system now has a block type registry (PR #8456) categorizing all 16 block types as YAML or CONTENT. Nodes 1.1-1.4 eliminated duplication and added error reporting; nodes 2.1-2.2 added the registry and category-aware parsing. The final node (2.3) adds parameterized round-trip tests proving that every registered block type survives render → parse → verify correctly.

**Dependency:** PR #8456 (block type registry) must be in the branch. It's merged in the Graphite stack but not yet on master. This plan should stack on top of #8456's branch or wait for it to land.

## What "Round-Trip" Means Per Category

- **YAML blocks with schemas** (8 types): Create `MetadataBlock` with valid data → `render_metadata_block()` → `parse_metadata_blocks()` → verify `result.blocks[0].data` matches original data, no errors
- **YAML blocks without schemas** (5 types): Same flow — construct with representative YAML data → render → parse → verify
- **CONTENT blocks** (3 types): Render with appropriate renderer → `parse_metadata_blocks()` → verify block lands in `result.content_blocks` with correct key and body content, not in `result.blocks` or `result.errors`

## Implementation

### New test file

**File:** `tests/unit/gateways/github/metadata_blocks/test_round_trip.py`

Single new file with parameterized tests covering all 16 registered block types.

### Test structure

```python
# 1. Registry-driven parameterization
#    Use get_all_block_types() to parameterize, ensuring tests stay in sync
#    with the registry automatically.

# 2. YAML round-trip test (parameterized over all 13 YAML block keys)
@pytest.mark.parametrize("key", [info.key for info in get_yaml_block_types()])
def test_yaml_block_round_trip(key: str) -> None:
    """Render → parse → verify for every YAML block type."""
    data = SAMPLE_DATA[key]  # fixture dict per block type
    block = MetadataBlock(key=key, data=data)
    rendered = render_metadata_block(block)
    result = parse_metadata_blocks(rendered)
    assert not result.has_errors
    assert len(result.blocks) == 1
    assert result.blocks[0].key == key
    assert result.blocks[0].data == data
    assert len(result.content_blocks) == 0

# 3. Content block round-trip test (parameterized over 3 content keys)
@pytest.mark.parametrize("key", [info.key for info in get_content_block_types()])
def test_content_block_round_trip(key: str) -> None:
    """Render → parse → verify for every CONTENT block type."""
    rendered = CONTENT_RENDERERS[key](SAMPLE_CONTENT[key])
    result = parse_metadata_blocks(rendered)
    assert len(result.blocks) == 0
    assert len(result.errors) == 0
    assert len(result.content_blocks) == 1
    assert result.content_blocks[0].key == key

# 4. Schema validation round-trip (parameterized over 8 schema-backed keys)
#    For schema-backed types, also verify that the factory functions produce
#    blocks that round-trip correctly.
@pytest.mark.parametrize("key", SCHEMA_BACKED_KEYS)
def test_schema_factory_round_trip(key: str) -> None:
    """Factory → render → parse → schema.validate() for schema-backed types."""
    block = FACTORY_BLOCKS[key]  # pre-built from factory functions
    rendered = render_metadata_block(block)
    result = parse_metadata_blocks(rendered)
    assert not result.has_errors
    info = get_block_type(key)
    info.schema.validate(result.blocks[0].data)

# 5. Registry completeness guard
def test_all_registered_types_have_sample_data() -> None:
    """Every registered block type has sample data for round-trip testing."""
    all_keys = set(get_all_block_types().keys())
    yaml_keys = set(SAMPLE_DATA.keys())
    content_keys = set(SAMPLE_CONTENT.keys())
    assert yaml_keys | content_keys == all_keys
```

### Sample data fixtures

Define `SAMPLE_DATA` dict mapping each YAML block key to a representative valid data dict. For schema-backed types, use data that passes schema validation. For schemaless types, use representative YAML dicts observed in production (e.g., from the objective body in this very issue).

Define `SAMPLE_CONTENT` dict mapping each content block key to representative markdown content.

Define `CONTENT_RENDERERS` dict mapping content block keys to their render functions:
- `plan-body` → `render_plan_body_block(create_plan_body_block(content))`
- `objective-body` → `render_objective_body_block(content)`
- `planning-session-prompts` → manual HTML comment wrapping (no dedicated renderer exists)

Define `FACTORY_BLOCKS` dict mapping schema-backed keys to blocks created via factory functions:
- `erk-implementation-status` → `create_implementation_status_block(...)`
- `erk-worktree-creation` → `create_worktree_creation_block(...)`
- `erk-plan` → `create_plan_block(...)`
- `submission-queued` → `create_submission_queued_block(...)`
- `workflow-started` → `create_workflow_started_block(...)`
- `plan-header` → `create_metadata_block(key="plan-header", data=..., schema=PlanHeaderSchema())`
- `objective-header` → `create_objective_header_block(...)`
- `plan-retry` → `create_metadata_block(key="plan-retry", data=..., schema=PlanRetrySchema())`

### Key files to modify/create

| File | Action |
|------|--------|
| `tests/unit/gateways/github/metadata_blocks/test_round_trip.py` | **CREATE** — all round-trip tests |

No production code changes needed. This is a test-only node.

### Imports needed from PR #8456

```python
from erk_shared.gateway.github.metadata.registry import (
    get_all_block_types,
    get_block_type,
    get_content_block_types,
    get_yaml_block_types,
)
```

## Verification

1. Run scoped tests: `pytest tests/unit/gateways/github/metadata_blocks/test_round_trip.py -v`
2. Run full metadata test suite: `pytest tests/unit/gateways/github/metadata_blocks/ -v`
3. Run `make fast-ci` for full lint + type check + unit tests
4. Verify parameterization covers all 16 block types (check test count matches registry size)
