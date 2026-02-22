# Remove run_url gate from land PR command

## Context

The TUI dashboard command palette hides the "land" command when `run_url` is `None`. This prevents landing PRs that haven't been run remotely yet. The user wants to remove this restriction.

## Change

**File:** `src/erk/tui/commands/registry.py`, lines 198-211

Remove `and ctx.row.run_url is not None` from the `land_pr` command's `is_available` predicate:

```python
# Before
is_available=lambda ctx: (
    _is_plan_view(ctx)
    and ctx.row.pr_number is not None
    and ctx.row.pr_state == "OPEN"
    and ctx.row.run_url is not None
),

# After
is_available=lambda ctx: (
    _is_plan_view(ctx)
    and ctx.row.pr_number is not None
    and ctx.row.pr_state == "OPEN"
),
```

## Verification

Update the test at `tests/tui/commands/test_registry.py` (line ~191-203) that asserts `land_pr` is NOT available when `run_url` is `None` — remove or invert that test case since it's no longer the expected behavior.
