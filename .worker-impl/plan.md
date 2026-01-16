# Plan: Add Branch Display to `erk plan view` (Plan-Header Approach)

## Summary

Add a `branch_name` field to the plan-header schema and display it in `erk plan view`. This persists the branch in GitHub metadata rather than relying on local worktree discovery.

## Current State

- `worktree_name` field exists in plan-header schema but is **never set** (always `None` at creation, `update_plan_header_worktree_name()` exists but is never called)
- Branch info only discoverable via local worktree inspection
- Lost when worktree is deleted

## Proposed Change

### Part 1: Add `branch_name` to Plan-Header Schema

Add a new optional field `branch_name` following the existing pattern:

**File: `packages/erk-shared/src/erk_shared/github/metadata/schemas.py`**
1. Add field constant: `BRANCH_NAME: Literal["branch_name"] = "branch_name"`
2. Add to `PlanHeaderFieldName` union type
3. Add to `optional_fields` set in `PlanHeaderSchema`
4. Add validation logic (string or null, non-empty when provided)

**File: `packages/erk-shared/src/erk_shared/github/metadata/plan_header.py`**
1. Add `branch_name: str | None` parameter to `create_plan_header_block()` and `format_plan_header_body()`
2. Add extraction function: `extract_plan_header_branch_name(issue_body: str) -> str | None`
3. Add update function: `update_plan_header_branch_name(issue_body: str, branch_name: str) -> str`

### Part 2: Display Branch in `erk plan view`

**File: `src/erk/cli/commands/plan/view.py`**

Display the branch after URL in the main metadata section:
```
State: OPEN | ID: #4978
URL: https://github.com/...
Branch: P4978-my-feature  <-- NEW LINE (only if set)
Labels: [erk-plan]
```

**Logic:**
1. Extract `branch_name` from plan-header
2. If not found, fall back to local worktree discovery (for backward compat with older plans)
3. Display if found, omit if not

### Part 3: Set Branch When Implementation Starts

**File: `src/erk/cli/commands/exec/scripts/impl_signal.py`**

This script already captures both `worktree_name` and `branch_name` at implementation start (lines 187-195) but only posts them in comments. We'll update the plan-header too.

**Approach:** Create a combined update function `update_plan_header_worktree_and_branch()` that sets both fields atomically. Call it from `_signal_started()` after `update_plan_header_local_impl_event()`.

```python
# In _signal_started(), after line 255:
updated_body = update_plan_header_worktree_and_branch(
    issue_body=updated_body,
    worktree_name=worktree_name,
    branch_name=branch_name,
)
```

**Why combined?** Both fields are set at the same time (implementation start), so a single atomic update is cleaner and more efficient than two separate API calls.

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/.../schemas.py` | Add `BRANCH_NAME` constant and validation |
| `packages/erk-shared/.../plan_header.py` | Add `branch_name` to create/format, add extract function, add `update_plan_header_worktree_and_branch()` |
| `src/erk/cli/commands/plan/view.py` | Display branch from plan-header with fallback |
| `src/erk/cli/commands/exec/scripts/impl_signal.py` | Call `update_plan_header_worktree_and_branch()` in `_signal_started()` |
| `tests/shared/github/test_plan_header_extraction.py` | Schema validation tests |
| `tests/shared/github/test_metadata_extraction.py` | Update function tests |
| `tests/commands/plan/test_view.py` | Display tests |
| `tests/unit/cli/commands/exec/scripts/test_impl_signal.py` | Test branch_name is set in plan-header |

## Test Strategy

1. **Schema tests:** Verify `branch_name` field validates correctly
2. **Extraction tests:** Verify `extract_plan_header_branch_name()` returns value from plan-header
3. **Update tests:** Verify `update_plan_header_branch_name()` updates the field
4. **View tests:**
   - Plan with `branch_name` in header → displays Branch field
   - Plan without `branch_name` but with local worktree → displays Branch field (fallback)
   - Plan without either → no Branch field

## Verification

1. Run schema tests: `uv run pytest tests/shared/github/test_plan_header_extraction.py`
2. Run view tests: `uv run pytest tests/commands/plan/test_view.py`
3. Manual test: `erk plan view <issue>` for a plan with existing worktree