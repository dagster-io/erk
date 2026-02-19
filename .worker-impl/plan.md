# Plan: Add `depends_on` to Roadmap Rendering (Nodes 1.2 + 1.3)

Part of Objective #7390, Nodes 1.2 + 1.3

## Context

PR #7471 introduced schema_version 3 with `depends_on: list[str]` on `RoadmapNode` and updated the parser/serializer. However, two rendering surfaces don't yet support it:

1. The `objective-render-roadmap` exec script — used to create new objectives from JSON input — ignores `depends_on` in its input and always passes `depends_on=None` to `RoadmapNode`.
2. `render_roadmap_tables()` — used to display roadmap status in objective bodies — renders only 5 columns (Node, Description, Status, Plan, PR) with no dependency visibility.

This plan merges nodes 1.2 and 1.3 because they are tightly coupled: both add `depends_on` awareness to rendering, and the exec script already calls `render_roadmap_block_inner()` which handles the metadata block correctly.

## Design Decision: Conditional Column

Add the "Depends On" column **only when any node has `depends_on` specified** (mirroring the conditional serialization pattern in `render_roadmap_block_inner()`). This keeps tables clean for sequential roadmaps.

## Implementation

### Phase 1: `objective-render-roadmap` exec script

**File:** `src/erk/cli/commands/exec/scripts/objective_render_roadmap.py`

#### 1a. Update `_validate_input()` — accept optional `depends_on` on steps

After the existing step field validation (line 89-91), add validation for optional `depends_on`:
- If present, must be a list
- Each item must be a string
- If absent, that's fine (remains `None`)

#### 1b. Update `_render_roadmap()` — pass `depends_on` through and add column

- Convert step's `depends_on` list to tuple when constructing `RoadmapNode` (line 135-144)
- Before rendering tables, check if any step across all phases has `depends_on`
- If yes, render 6-column table: `| Node | Description | Depends On | Status | Plan | PR |`
- If no, render existing 5-column table (unchanged)
- Format depends_on values: `None`/`()` → `-`, non-empty → comma-separated IDs

### Phase 2: `render_roadmap_tables()`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`

#### 2a. Add conditional "Depends On" column

- Check if any node across all phases has `depends_on is not None`
- If yes, insert "Depends On" column between "Description" and "Status"
- Format: `None`/`()` → `-`, non-empty tuple → comma-separated IDs (e.g., `1.1, 1.2`)

### Phase 3: Tests

#### 3a. Exec script tests

**File:** `tests/unit/cli/commands/exec/scripts/test_objective_render_roadmap.py`

New tests:
- `test_validate_input_step_with_depends_on` — valid `depends_on` list accepted
- `test_validate_input_step_depends_on_not_list` — rejects non-list `depends_on`
- `test_validate_input_step_depends_on_non_string_items` — rejects non-string items
- `test_render_roadmap_with_depends_on` — 6-column table rendered when `depends_on` present
- `test_render_roadmap_without_depends_on_unchanged` — 5-column table unchanged when no `depends_on`
- `test_render_roadmap_depends_on_metadata_roundtrip` — metadata block parses correctly with `depends_on`

#### 3b. `render_roadmap_tables` tests

**File:** `packages/erk-shared/tests/unit/github/metadata/test_roadmap.py`

New tests in `TestRenderRoadmapTables`:
- `test_depends_on_column_when_present` — 6-column table with depends_on values
- `test_no_depends_on_column_when_all_none` — 5-column table unchanged
- `test_depends_on_formatting` — `()` → `-`, `("1.1",)` → `1.1`, `("1.1", "1.2")` → `1.1, 1.2`

## Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/objective_render_roadmap.py` | Accept + render `depends_on` |
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` | Add column to `render_roadmap_tables()` |
| `tests/unit/cli/commands/exec/scripts/test_objective_render_roadmap.py` | New tests |
| `packages/erk-shared/tests/unit/github/metadata/test_roadmap.py` | New tests |

## Verification

1. Run exec script tests: `pytest tests/unit/cli/commands/exec/scripts/test_objective_render_roadmap.py`
2. Run roadmap tests: `pytest packages/erk-shared/tests/unit/github/metadata/test_roadmap.py`
3. Run frontmatter roundtrip tests: `pytest packages/erk-shared/tests/unit/github/metadata/test_roadmap_frontmatter.py`
4. Run ty type checker on modified files
5. Run ruff lint on modified files