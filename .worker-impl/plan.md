# Refactor Trunk Branch Validation to Use Ensure.invariant()

## Summary

Refactor the trunk branch validation check in `create_cmd.py` (lines 105-112) to use the `Ensure.invariant()` pattern for consistent CLI error handling.

## Current Code

```python
# Lines 105-112 in src/erk/cli/commands/wt/create_cmd.py
if branch == trunk_branch:
    user_output(
        f'Error: Cannot create worktree for trunk branch "{trunk_branch}".\n'
        f"The trunk branch should be checked out in the root worktree.\n"
        f"To switch to {trunk_branch}, use:\n"
        f"  erk checkout root"
    )
    raise SystemExit(1)
```

## Refactored Code

```python
Ensure.invariant(
    branch != trunk_branch,
    f'Cannot create worktree for trunk branch "{trunk_branch}".\n'
    f"The trunk branch should be checked out in the root worktree.\n"
    f"To switch to {trunk_branch}, use:\n"
    f"  erk checkout root",
)
```

## Implementation Steps

1. **Edit `src/erk/cli/commands/wt/create_cmd.py`**
   - Replace lines 105-112 with `Ensure.invariant()` call
   - Note: `Ensure` is already imported at line 26, so no import changes needed
   - Note: `Ensure.invariant()` auto-prepends "Error: " in red, so we remove that from the message

2. **Run tests** to verify no regressions

## Files to Modify

- `src/erk/cli/commands/wt/create_cmd.py` (lines 105-112)

## Testing

Run relevant tests:
```bash
uv run pytest tests/commands/wt/test_create.py -v
```