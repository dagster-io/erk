# Plan: Introduce `PlanHeaderData` frozen dataclass

## Context

`plan_header.py` (~1518 lines, ~40 public functions) trades in raw `dict[str, Any]` repeatedly. Every `extract_*` re-parses the metadata block from the issue body string. Every `update_*` repeats a 7-line find/copy/set/validate/create/render/replace pattern. The two constructor functions (`create_plan_header_block`, `format_plan_header_body`) each take ~27 keyword args that callers pass with most set to `None`. All field access is untyped (`block.data.get(STRING_KEY) -> Any`).

Introducing a typed frozen dataclass gives: parse-once/access-many, typed field access, `dataclasses.replace()` for updates, and a single object to pass instead of 27 args.

**Scope**: Phase 1 only. Introduce `PlanHeaderData`, rewrite internals of `plan_header.py` to use it, but keep all existing function signatures unchanged. No caller changes, no `Plan.header_fields` changes.

## Step 1: Create `plan_header_data.py`

**New file**: `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header_data.py`

Frozen dataclass with 2 required fields + 31 optional fields (all `T | None = None`):

```python
@dataclass(frozen=True)
class PlanHeaderData:
    # Required
    created_at: str
    created_by: str
    # Optional (31 fields, all default None)
    worktree_name: str | None = None
    branch_name: str | None = None
    plan_comment_id: int | None = None
    ci_summary_comment_id: int | None = None
    # ... (all 31 optional fields from PlanHeaderSchema)
    node_ids: tuple[str, ...] | None = None  # tuple, not list
    lifecycle_stage: LifecycleStageValue | None = None
```

**`schema_version`** is NOT a field — always `"2"`, injected by `to_dict()`.

**`node_ids`** uses `tuple[str, ...]` (frozen-dataclass convention). Converted to/from `list` at serialization boundaries.

Four methods:
- `from_dict(cls, data: dict[str, Any]) -> PlanHeaderData` — classmethod, converts parsed YAML dict to typed dataclass. Handles `node_ids` list→tuple.
- `from_issue_body(cls, issue_body: str) -> PlanHeaderData | None` — classmethod, calls `find_metadata_block` once, delegates to `from_dict`.
- `to_dict(self) -> dict[str, Any]` — serializes back. Injects `schema_version: "2"`. Converts `node_ids` tuple→list. Only includes optional fields when non-None (preserving current YAML output behavior of `create_plan_header_block`).
- `to_metadata_block(self) -> MetadataBlock` — calls `to_dict()`, validates via `PlanHeaderSchema`, returns `MetadataBlock`.

Imports from: `schemas.py` (field constants, Literal types), `types.py` (`BlockKeys`, `MetadataBlock`), `core.py` (`find_metadata_block`). No import cycle risk.

## Step 2: Add `_update_plan_header` helper to `plan_header.py`

Private helper that eliminates the 7-line boilerplate repeated in ~12 update functions:

```python
def _update_plan_header(issue_body: str, **updates: Any) -> str:
    block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
    if block is None:
        raise ValueError("plan-header block not found in issue body")
    updated_data = dict(block.data)
    updated_data.update(updates)
    schema = PlanHeaderSchema()
    schema.validate(updated_data)
    new_block = MetadataBlock(key=BlockKeys.PLAN_HEADER, data=updated_data)
    return replace_metadata_block_in_body(
        issue_body, BlockKeys.PLAN_HEADER, render_metadata_block(new_block)
    )
```

## Step 3: Rewrite `create_plan_header_block` to use `PlanHeaderData`

The body becomes: construct `PlanHeaderData(...)`, call `.to_metadata_block()`. Function signature unchanged.

## Step 4: Rewrite all `update_plan_header_*` functions to use `_update_plan_header`

Each ~12-line function becomes ~3-5 lines. Example:

```python
def update_plan_header_dispatch(issue_body, run_id, node_id, dispatched_at):
    return _update_plan_header(
        issue_body,
        **{LAST_DISPATCHED_RUN_ID: run_id, LAST_DISPATCHED_NODE_ID: node_id, LAST_DISPATCHED_AT: dispatched_at},
    )
```

Functions affected (12):
- `update_plan_header_dispatch`
- `update_plan_header_objective_issue`
- `update_plan_header_comment_id`
- `update_plan_header_local_impl`
- `update_plan_header_worktree_name`
- `update_plan_header_worktree_and_branch`
- `update_plan_header_local_impl_event`
- `update_plan_header_remote_impl`
- `update_plan_header_remote_impl_event`
- `update_plan_header_learn_event`
- `update_plan_header_learn_status`
- `update_plan_header_learn_result`
- `update_plan_header_learn_plan_completed`
- `update_plan_header_learn_materials_branch`
- `update_plan_header_ci_summary_comment_id`
- `update_plan_header_session_branch`

## Step 5: Create tests for `PlanHeaderData`

**New file**: `tests/unit/gateways/github/metadata_blocks/test_plan_header_data.py`

Tests:
1. `test_from_dict_all_fields` — all 34 fields populated, verify typed access
2. `test_from_dict_minimal` — only required fields, optional fields are None
3. `test_from_dict_node_ids_list_to_tuple` — list→tuple conversion
4. `test_to_dict_round_trip` — PlanHeaderData→to_dict→schema validates
5. `test_to_dict_injects_schema_version` — always includes `"2"`
6. `test_to_dict_converts_tuple_to_list` — node_ids tuple→list
7. `test_to_metadata_block` — returns valid MetadataBlock
8. `test_from_issue_body_parses` — end-to-end with rendered body
9. `test_from_issue_body_returns_none` — no metadata block
10. `test_yaml_round_trip` — create→render→parse→verify fields match
11. `test_frozen` — assignment raises FrozenInstanceError

## What does NOT change

- All existing function signatures and return types in `plan_header.py`
- No caller modifications (planned_pr.py, dispatch commands, etc.)
- `Plan.header_fields: dict[str, object]` and `conversion.py` accessor helpers
- `PlanHeaderSchema` validation logic in `schemas.py`
- `format_plan_header_body_for_test()` in test helpers

## Files to modify

| File | Action |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header_data.py` | Create: PlanHeaderData dataclass |
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py` | Modify: add _update_plan_header, rewrite create_plan_header_block + all update_* functions |
| `tests/unit/gateways/github/metadata_blocks/test_plan_header_data.py` | Create: 11 tests |

## Verification

1. Run `pytest tests/unit/gateways/github/metadata_blocks/` — new tests + existing round-trip/update tests
2. Run `pytest tests/shared/github/` — existing extraction/validation tests (93+ tests)
3. Run `ty` and `ruff` for type/lint checks
