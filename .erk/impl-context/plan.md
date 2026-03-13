# Fix: TUI land-execute --plan-number mismatch + detail screen bug

## Context

Part of **O9109 node 6.1** (rename internal plan_number/plan_id params in TUI). Two bugs found:

1. `workers.py:271` passes `--plan-number` but `land-execute` only accepts `--linked-pr-number` — causes landing to fail from TUI with error toast
2. `plan_detail_screen.py:855-860` calls `_land_pr_async()` with positional args (function is keyword-only via `*`) and missing `plan_number` — causes `TypeError` when landing from detail screen

## Changes

### 1. `src/erk/tui/operations/workers.py:271`

```python
# Before
command.append(f"--plan-number={plan_number}")
# After
command.append(f"--linked-pr-number={plan_number}")
```

### 2. `src/erk/tui/screens/plan_detail_screen.py:855-860`

```python
# Before (positional args, missing plan_number)
self.app._land_pr_async(
    op_id,
    row.pr_number,
    row.pr_head_branch,
    row.objective_issue,
)
# After (keyword args, matching palette.py:213 pattern)
plan_number = row.pr_number if not row.is_learn_plan else None
self.app._land_pr_async(
    op_id=op_id,
    pr_number=row.pr_number,
    branch=row.pr_head_branch,
    objective_issue=row.objective_issue,
    plan_number=plan_number,
)
```

## Verification

1. Run `pytest tests/tui/` to check for regressions
2. Run `ty` for type checking
3. Manual: `erk dash -i`, land a PR from both the main list and the detail screen
