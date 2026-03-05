# Plan: Add print statement to src/erk/__init__.py

## Context
User requested adding a print statement saying "for dgibson after plubming" to the first Python file found in the project.

The first project Python file (by glob order in `src/erk/`) is `src/erk/__init__.py`.

## Change

**File:** `src/erk/__init__.py`

Add `print("for dgibson after plubming")` at the top of the `main()` function, before `cli()`.

### Before (lines 10-12):
```python
def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
```

### After:
```python
def main() -> None:
    """CLI entry point used by the `erk` console script."""
    print("for dgibson after plubming")
    cli()
```

## Verification
Run `erk --help` and verify the print statement output appears before the help text.
