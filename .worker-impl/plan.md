# Fix .erk/bin/ description in erk init

## Summary

Change the gitignore prompt description from "compiled CLI binaries" to "generated shell scripts" since `.erk/bin/` actually stores shell scripts (`activate.sh`, `land.sh`), not compiled binaries.

## Change

**File:** `src/erk/cli/commands/init/main.py`

**Line 233:** Change:
```python
"Add .erk/bin/ to .gitignore (compiled CLI binaries)?",
```

To:
```python
"Add .erk/bin/ to .gitignore (generated shell scripts)?",
```

## Verification

1. Run `erk init` in a test repo and verify the prompt shows the new description
2. No tests to update - this is just a user-facing string