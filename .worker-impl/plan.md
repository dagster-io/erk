# Plan: Atomic Batch Status Update for `--all-unblocked` Dispatch

Part of Objective #7390, Node 2.2

## Context

When `erk objective plan --all-unblocked` dispatches multiple nodes in parallel, each node's status is updated individually via separate GitHub API calls (fetch issue body, modify one node, write back). With N unblocked nodes, this results in N read-modify-write cycles against the same issue, creating:

1. **Unnecessary API calls** — N fetches + N writes instead of 1 fetch + 1 write
2. **Race condition exposure** — between writes, concurrent processes (e.g., a fast-completing workflow) could modify the issue, causing data loss

The fix: collect all dispatch results first, then apply all node status updates to the issue body in memory and write once.

## Implementation

### Step 1: Add `_batch_update_objective_nodes()` to `plan_cmd.py`

**File:** `src/erk/cli/commands/objective/plan_cmd.py`

Create a new function that handles multiple (node_id, pr_number) pairs atomically:

```python
@dataclass(frozen=True)
class DispatchedNode:
    node_id: str
    pr_number: int

def _batch_update_objective_nodes(
    issues: GitHubIssues,
    repo_root: Path,
    *,
    issue_number: int,
    dispatched: list[DispatchedNode],
) -> None:
```

Logic:
1. Fetch the issue body once via `issues.get_issue()`
2. Loop through `dispatched`, calling `_replace_node_refs_in_body()` for each, accumulating changes on the in-memory body string (same pattern as `update-objective-node` exec script lines 426-465)
3. Write the final body back via `issues.update_issue_body()` — single API call
4. Update the v2 comment table: fetch comment once, apply all node updates via `_replace_table_in_text()`, write once

### Step 2: Refactor `_handle_all_unblocked()` to use batch update

**File:** `src/erk/cli/commands/objective/plan_cmd.py` (lines 218-280)

Split the current single loop into two phases:

**Phase 1 — Dispatch all nodes, collect results:**
```python
dispatched: list[DispatchedNode] = []
for node, phase_name in resolved.nodes:
    dispatch_result = dispatch_one_shot(ctx, params=params, dry_run=dry_run)
    if dispatch_result is not None:
        dispatched.append(DispatchedNode(node_id=node.id, pr_number=dispatch_result.pr_number))
```

**Phase 2 — Single atomic update:**
```python
if dispatched:
    _batch_update_objective_nodes(
        ctx.issues, ctx.repo.root,
        issue_number=resolved.issue_number,
        dispatched=dispatched,
    )
```

Keep existing `_update_objective_node()` unchanged — it's still used by `_handle_one_shot()` for single-node dispatch.

### Step 3: Update tests

**File:** `tests/unit/cli/commands/objective/test_plan_cmd.py`

Update `TestHandleAllUnblocked.test_updates_objective_nodes_to_planning`:
- Verify atomicity: assert `len(issues._updated_bodies) == 1` (single body write for all nodes)
- Verify both nodes appear as "planning" in the final body
- Verify both draft PR numbers appear in the final body

Add a new test:
- `test_batch_update_atomicity`: Dispatch 2 nodes, verify exactly 1 `update_issue_body` call was made (not 2)

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/objective/plan_cmd.py` | Add `DispatchedNode` dataclass, add `_batch_update_objective_nodes()`, refactor `_handle_all_unblocked()` |
| `tests/unit/cli/commands/objective/test_plan_cmd.py` | Update existing test, add atomicity test |

## Reuse

- `_replace_node_refs_in_body()` from `update_objective_node.py` (already imported in plan_cmd.py line 9)
- `_replace_table_in_text()` from `update_objective_node.py` (already imported in plan_cmd.py line 10)
- `extract_metadata_value()` from `erk_shared` (already imported in plan_cmd.py line 28)
- Pattern from `update_objective_node.py` lines 421-503 (accumulate changes in memory, write once)

## Verification

1. Run existing tests: `pytest tests/unit/cli/commands/objective/test_plan_cmd.py`
2. Run ty type checker on modified files
3. Run ruff linter
4. Verify the new atomicity test passes — assert exactly 1 `update_issue_body` call for multi-node dispatch
5. Verify existing `test_dispatches_each_node` and `test_dry_run_shows_preview` still pass unchanged