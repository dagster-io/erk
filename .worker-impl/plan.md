# Replace Manual Error Check with Ensure.not_none()

## Summary

Replace the manual None check in `config.py` with `Ensure.not_none()` for consistency.

## Location

**File:** `src/erk/cli/commands/config.py:104-107`

## Current Code

```python
if ctx.global_config is None:
    config_path = ctx.config_store.path()
    user_output(f"Global config not found at {config_path}")
    raise SystemExit(1)
```

## Replacement

```python
Ensure.not_none(ctx.global_config, f"Global config not found at {ctx.config_store.path()}")
```

## Changes Required

1. Add import at top of file: `from erk.cli.ensure import Ensure`
2. Replace lines 104-107 with the single `Ensure.not_none()` call
