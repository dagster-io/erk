# Fix: `find_graph_next_step` should fall back to `in_progress` steps

## Context

When all remaining objective steps are `in_progress` (none are `pending`), `find_graph_next_step` returns `None` and the TUI "next step" column shows `-`. This is misleading — the objective isn't done, there's just no *pending* work. The first in-progress step is the logical "next step" to show.

Affected objectives today: #7161 (25/27, 2 in_progress), #7129 (10/13, 3 in_progress).

## Change

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`

In `find_graph_next_step` (line 172-175), change the node search to try `pending` first, then fall back to `in_progress`:

```python
# Current:
target_node = next(
    (node for node in graph.nodes if node.status == "pending"),
    None,
)

# New:
target_node = next(
    (node for node in graph.nodes if node.status == "pending"),
    None,
)
if target_node is None:
    target_node = next(
        (node for node in graph.nodes if node.status == "in_progress"),
        None,
    )
```

No changes needed to callers — the return type (`dict[str, str] | None`) is unchanged, and the semantics ("what comes next") are preserved.

## Tests

**File:** `packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py`

Add a test to `TestFindGraphNextStep`:
- `test_falls_back_to_in_progress_when_no_pending` — all remaining steps are `in_progress`, verify the first one is returned

## Verification

- Run existing tests: `pytest packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py::TestFindGraphNextStep`
- Verify in TUI that objectives with only `in_progress` remaining steps now show a next step