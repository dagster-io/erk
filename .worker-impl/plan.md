# Plan: Add `.erk/config.local.toml` to gitignore check in `erk doctor`

## Summary

Add `.erk/config.local.toml` to the required gitignore entries checked by `erk doctor`. The init process already prompts users to add this entry; the doctor check just needs to verify it.

## Changes

### 1. Update `check_gitignore_entries` in `src/erk/core/health_checks.py`

**Line 723**: Add `.erk/config.local.toml` to the `required_entries` list:

```python
# Before
required_entries = [".erk/scratch/", ".impl/"]

# After
required_entries = [".erk/scratch/", ".impl/", ".erk/config.local.toml"]
```

## Verification

1. Run health check tests: `pytest tests/ -k "gitignore" -v`
2. Manual test: Run `erk doctor` in a repo missing the entry to confirm it reports the issue