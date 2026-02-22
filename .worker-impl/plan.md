# Objective TUI: Slug + State Sparkline Redesign

## Context

The objectives table in `erk dash` has poor info density. The title column is 50 chars wide showing full "Objective: ..." text when slugs exist in metadata. The "fly", "next node", and "deps" columns consume 65 chars to convey graph state that could be shown as a compact sparkline. This redesign replaces those columns with a slug and a state sparkline showing each node's status in graph order.

**Before:** `issue | title(50) | prog(5) | fly(3) | next node(50) | deps(12) | updated(7) | created by(12)`
**After:** `issue | slug(25) | prog(5) | state(20) | updated(7) | created by(12)`

Sparkline example: `✓✓✓▶▶○○○○` (3 done, 2 active, 4 pending)

## Changes

### 1. Add `extract_objective_slug()` convenience function

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`

Add alongside existing `extract_objective_header_comment_id()` (~line 749):

```python
def extract_objective_slug(issue_body: str) -> str | None:
    return extract_metadata_value(issue_body, "objective-header", "slug")
```

### 2. Update PlanRowData fields

**File:** `src/erk/tui/data/types.py`

- Remove: `objective_next_node_display`, `objective_deps_display`, `objective_in_flight_display`
- Add: `objective_slug_display: str` (slug or stripped title fallback, max 25 chars)
- Add: `objective_state_display: str` (sparkline string like `✓✓✓▶▶○○○○`)

### 3. Compute slug + sparkline in data provider

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` (lines ~648-683)

Replace the existing next_node/deps/in_flight computation with:

- **Slug:** Call `extract_objective_slug(plan.body)`. Fallback: strip "Objective: " prefix from title, truncate to 25 chars.
- **Sparkline:** Iterate `graph.nodes` in position order, map each `node.status` to a symbol:
  - `done` → `✓`
  - `in_progress` → `▶`
  - `planning` → `▶`
  - `pending` → `○`
  - `blocked` → `⊘`
  - `skipped` → `-`

Build the sparkline string by joining the symbols. Store as `objective_state_display`.

### 4. Update plan_table columns and row rendering

**File:** `src/erk/tui/widgets/plan_table.py`

**`_setup_columns()` (lines 160-175):** Replace objectives columns:
```python
self.add_column("issue", key="plan", width=6)
self.add_column("slug", key="slug", width=25)
self.add_column("prog", key="progress", width=5)
self.add_column("state", key="state", width=20)
self.add_column("updated", key="updated", width=7)
self.add_column("created by", key="author", width=12)
```

**`_row_to_values()` (lines 275-286):** Update objectives tuple:
```python
return (
    plan_cell,
    row.objective_slug_display,
    row.objective_progress_display,
    Text(row.objective_state_display),  # Rich Text for potential future coloring
    row.updated_display,
    row.author,
)
```

### 5. Update fake data provider

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`

- Remove parameters: `objective_next_node_display`, `objective_deps_display`, `objective_in_flight_display`
- Add parameters: `objective_slug_display: str = "-"`, `objective_state_display: str = "-"`

### 6. Update tests

**Files:**
- `tests/tui/test_plan_table.py` — Update `TestObjectivesViewRowConversion` tests: new tuple length (6 instead of 8), new field assertions
- `tests/unit/cli/commands/exec/scripts/test_dash_data.py` — Update serialization field lists
- `tests/tui/commands/test_execute_command.py` — Update any objective field references

### 7. Add unit test for sparkline generation

Extract the status-to-symbol mapping as a pure function (e.g., `build_state_sparkline(nodes: tuple[ObjectiveNode, ...]) -> str`) in `dependency_graph.py` and add a focused unit test.

## Verification

1. Run `make fast-ci` to ensure all tests pass
2. Run `erk dash` and verify objectives tab shows slug + sparkline columns
3. Verify sparkline accurately reflects node statuses for an objective with mixed states
