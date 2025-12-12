# Plan: Demo Ensure.not_none() in submit.py

## Summary

Replace verbose None-check error handling with `Ensure.not_none()` in a single call site.

## File to Modify

`src/erk/cli/commands/submit.py`

## Change

**Current code (lines 599-605):**
```python
original_branch = ctx.git.get_current_branch(repo.root)
if original_branch is None:
    user_output(
        click.style("Error: ", fg="red")
        + "Not on a branch (detached HEAD state). Cannot submit from here."
    )
    raise SystemExit(1)
```

**New code:**
```python
original_branch = Ensure.not_none(
    ctx.git.get_current_branch(repo.root),
    "Not on a branch (detached HEAD state). Cannot submit from here.",
)
```

## Why This Example Works

1. **File already imports `Ensure`** (line 17) - no new imports needed
2. **6 lines → 4 lines** - clear reduction in verbosity
3. **Type narrowing** - `Ensure.not_none()` returns `str` instead of `str | None`
4. **Same behavior** - identical error message and exit code
5. **Uses existing method** - no new Ensure method required