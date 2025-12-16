# Plan: Convert Error Check to Ensure Pattern in admin.py

## Summary

Replace a manual error checking block in `admin.py` with the `Ensure.not_none()` method from `ensure.py`.

## Target File

`/Users/schrockn/code/erk/src/erk/cli/commands/admin.py`

## Current Code (lines 49-53)

```python
# Check for GitHub identity
if repo.github is None:
    user_output(click.style("Error: ", fg="red") + "Not a GitHub repository")
    user_output("This command requires the repository to have a GitHub remote configured.")
    raise SystemExit(1)
```

## Proposed Change

```python
from erk.cli.ensure import Ensure

# Check for GitHub identity
github_id = Ensure.not_none(
    repo.github,
    "Not a GitHub repository. This command requires the repository to have a GitHub remote configured."
)
```

## Changes Required

1. Add import: `from erk.cli.ensure import Ensure`
2. Replace 4-line error block with single `Ensure.not_none()` call
3. Capture return value as `github_id` for use on line 58

## Notes

- `Ensure.not_none()` automatically adds the red "Error: " prefix
- The method raises `SystemExit(1)` on failure, matching current behavior
- Combining the two error messages into one (separated by period) maintains context
- Return value provides type narrowing from `str | None` to `str`