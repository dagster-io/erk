# Plan: Update Objective When Closing an Affiliated Plan

## Context

`erk plan close` closes a plan issue and its linked PRs, but when the plan is affiliated with an objective (via `objective_id`), it does not update the objective's roadmap. This leaves the objective with stale node data - nodes still show the closed plan reference and "in_progress" status. The fix adds a fail-open objective update step that resets matched nodes to "pending" and clears their plan references.

## Implementation

### 1. Add helper function to `objective_helpers.py`

**File:** `src/erk/cli/commands/objective_helpers.py`

Add `reset_objective_nodes_for_closed_plan(ctx, repo_root, *, plan_number, objective_id)`:

1. Fetch objective issue via `ctx.issues.get_issue(repo_root, objective_id)`
2. Parse roadmap via `parse_roadmap(issue.body)` to get phases/nodes
3. Find nodes where `node.plan == f"#{plan_number}"`
4. For each matched node, update the issue body via `_replace_node_refs_in_body(body, node_id, new_plan="", new_pr=None, explicit_status="pending")`
5. Write updated body back via `ctx.issues.update_issue_body()`
6. Update v2 markdown table in comment via `_replace_table_in_text()` + `ctx.issues.update_comment()` (using `extract_metadata_value` to find `objective_comment_id`)
7. Add comment to objective: `"Plan #{plan_number} was closed. Reset node(s) {node_list} to pending."`
8. Output: `"Updated objective #{objective_id}: reset node(s) {node_list} to pending"`

**Fail-open:** Wrap entire body in try/except that logs warning and emits `user_output` with yellow warning on failure. Plan close must never fail due to objective update.

**Imports to add:**
- `_replace_node_refs_in_body`, `_replace_table_in_text` from `update_objective_node.py` (already imported by `objective/plan_cmd.py` - established pattern)
- `parse_roadmap` from `erk_shared.gateway.github.metadata.roadmap`
- `extract_metadata_value` from `erk_shared.gateway.github.metadata.core`
- `BodyText` from `erk_shared.gateway.github.types`
- `IssueNotFound` from `erk_shared.gateway.github.issues.types`

### 2. Call helper from `close_cmd.py`

**File:** `src/erk/cli/commands/plan/close_cmd.py`

After `ctx.plan_store.close_plan()` (line 63), before final output (line 66):

```python
if result.objective_id is not None:
    reset_objective_nodes_for_closed_plan(
        ctx, repo_root,
        plan_number=number,
        objective_id=result.objective_id,
    )
```

### 3. Add tests

**File:** `tests/commands/plan/test_close.py`

Add a `_make_objective_body(plan_ref)` helper to generate a valid v2 objective-roadmap body with nodes referencing the given plan.

Test cases:
1. **Plan with objective resets roadmap nodes** - Node status becomes "pending", plan ref cleared, comment added to objective
2. **Multiple matched nodes** - All nodes referencing the plan get reset
3. **No matching nodes** - Plan has `objective_id` but no roadmap nodes reference it; no update, no error
4. **Objective not found** - Plan close succeeds with warning
5. **Update failure** - Exception during objective update; plan close still succeeds
6. **No objective** - `objective_id=None`; no objective update attempted (regression)

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/objective_helpers.py` | Add `reset_objective_nodes_for_closed_plan` |
| `src/erk/cli/commands/plan/close_cmd.py` | Call new helper when `objective_id` is set |
| `tests/commands/plan/test_close.py` | Add 6 test cases + helper for objective body |

## Key Existing Functions to Reuse

- `_replace_node_refs_in_body()` from `src/erk/cli/commands/exec/scripts/update_objective_node.py` - updates frontmatter YAML in body
- `_replace_table_in_text()` from same file - updates rendered markdown table in comment
- `parse_roadmap()` from `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` - parses roadmap phases/nodes
- `extract_metadata_value()` from `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py` - extracts `objective_comment_id`

## Verification

1. Run tests: `uv run pytest tests/commands/plan/test_close.py`
2. Run type checker on modified files
3. Run linter/formatter
