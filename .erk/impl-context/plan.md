# TUI: Show toast when learn plan is created on landing

## Context

When landing a PR from the TUI, learn plans are **not** being created at all. The TUI calls `erk exec land-execute --pr-number=N --branch=B -f` but does **not** pass `--plan-number`. Since `plan_id` is None in the execution state, the `create_learn_pr` pipeline step short-circuits immediately.

The CLI `erk land` works correctly because the validation pipeline's `resolve_plan_id` step populates `plan_id` before the execution pipeline runs. But the TUI bypasses validation and calls land-execute directly.

## Plan

### 1. Pass `--plan-number` from TUI to `land-execute`

**File:** `src/erk/tui/app.py` — `_land_pr_async` method (line ~842)

Add `--plan-number={row.plan_id}` to the command list. The plan_id is already available on `PlanRowData` and is passed to `_land_pr_async`. Update the method signature to accept `plan_id: int`.

At the call site (line ~1356), pass `row.plan_id`.

### 2. Show toast when learn plan is created

**File:** `src/erk/tui/app.py` — `_land_pr_async` method (line ~862)

After the successful landing toast, scan `result.output_lines` for the learn plan creation message. The `create_learn_pr` step outputs `"✓ Created learn plan #{N} for plan #{M}"` on success. Parse this to extract the learn plan number and show a toast.

```python
# After "Landed PR #N" toast
learn_pr = _extract_learn_plan_number(result)
if learn_pr is not None:
    self.call_from_thread(self.notify, f"Created learn plan #{learn_pr}", timeout=3)
```

Add a helper function `_extract_learn_plan_number(result: _OperationResult) -> int | None` that scans output lines with a regex for `Created learn plan #(\d+)`.

### 3. Skip learn plan for learn plans (cycle prevention)

At the call site (line ~1356), only pass `plan_id` when the row is NOT itself a learn plan:

```python
plan_id=row.plan_id if not row.is_learn_plan else None
```

This matches the existing cycle prevention in `_create_learn_pr_impl` but avoids unnecessary work.

## Files to modify

- `src/erk/tui/app.py` — `_land_pr_async` signature, command construction, output parsing, and call site

## Verification

1. Land a plan PR from the TUI — should see "Landed PR #N" toast followed by "Created learn plan #N" toast
2. Land a learn plan PR from the TUI — should see "Landed PR #N" toast only, no learn plan created
3. CLI `erk land` should be unaffected (it already passes plan_number through the validation pipeline)
