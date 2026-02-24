# Fix: TUI dispatch commands don't update run-id/status columns

## Context

When dispatching fix-conflicts (or address-remote) from the TUI dashboard, the run-id and run status columns never update. The workflow IS triggered, but the dispatch metadata (run_id, node_id) is never written back to the PR body's plan-header block. This means the subsequent refresh finds no dispatch info and shows "-".

The root cause: `maybe_update_plan_dispatch_metadata` has 3 guard clauses that silently return without writing metadata. Since the TUI captures subprocess output and only checks exit code, it shows a success toast even when metadata was never written.

## Changes

### 1. Add diagnostic output to silent early returns

**File:** `src/erk/cli/commands/pr/metadata_helpers.py`

In `maybe_update_plan_dispatch_metadata`, change each silent `return` to emit a `user_output` warning before returning:

- Guard 1 (`plan_id is None`): `"Note: No plan found for branch '{branch_name}' — skipping metadata update"`
- Guard 2 (`node_id is None`): `"Warning: Could not get node_id for run {run_id} — metadata not updated"`
- Guard 3 (`schema_version` check): `"Warning: Plan #{plan_id} has no plan-header block — metadata not updated"`

Apply the same pattern to `maybe_write_pending_dispatch_metadata` (2 early returns).

### 2. TUI: detect metadata write outcome from subprocess stderr

**File:** `src/erk/tui/app.py`

In `_fix_conflicts_remote_async` and `_address_remote_async`: after `subprocess.run`, check `result.stderr` for the existing success marker `"Updated dispatch metadata"`. If absent, append `"(metadata not updated)"` to the toast message so the user knows the run-id won't appear.

```python
result = subprocess.run(...)
metadata_updated = "Updated dispatch metadata" in result.stderr
if metadata_updated:
    self.call_from_thread(self.notify, f"Dispatched: ...", timeout=3)
else:
    self.call_from_thread(self.notify, f"Dispatched: ... (metadata not updated)", timeout=5)
```

### 3. Add tests for `maybe_update_plan_dispatch_metadata` early-return diagnostics

**File:** `tests/unit/cli/commands/pr/test_metadata_helpers.py`

The existing file only tests `maybe_write_pending_dispatch_metadata`. Add parallel tests for `maybe_update_plan_dispatch_metadata`:

- `test_non_plan_branch_skips_update` — branch that doesn't resolve to plan
- `test_missing_node_id_skips_update` — run_id exists but node_id fetch returns None
- `test_plan_without_header_skips_update` — plan exists but no plan-header block
- `test_successful_update_writes_metadata` — happy path: all guards pass, metadata written

Follow the existing pattern using `context_for_test`, `create_plan`, `_make_repo`.

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/pr/metadata_helpers.py` | Add `user_output` warnings to 5 early-return paths |
| `src/erk/tui/app.py` | Check `result.stderr` in 2 dispatch handlers |
| `tests/unit/cli/commands/pr/test_metadata_helpers.py` | Add 4 tests for `maybe_update_plan_dispatch_metadata` |

## Verification

1. Run existing tests: `pytest tests/unit/cli/commands/pr/test_metadata_helpers.py`
2. Run new tests: same file
3. Run TUI tests: `pytest tests/tui/`
4. Manual: `erk dash -i`, select a plan with a PR, dispatch fix-conflicts, verify run-id column updates after toast
