# Fix: Remove invalid `-f` flag from TUI plan submit

## Context

The TUI's "submit to queue" action fails with:
```
Failed to submit plan #8064: Usage: erk plan submit ISSUE_NUMBERS...
Error: No such option: -f
```

The `-f` flag was passed to `erk plan submit`, but that command doesn't accept it. The `-f`/`--force` flag exists on `erk pr submit`, not `erk plan submit`.

## Change

**File:** `src/erk/tui/app.py` line 677

Remove `-f` from the subprocess args:

```python
# Before
["erk", "plan", "submit", str(plan_id), "-f"]

# After
["erk", "plan", "submit", str(plan_id)]
```

## Verification

- Run `erk plan submit -h` to confirm no `-f` flag exists
- Run TUI and trigger submit action to verify it works
