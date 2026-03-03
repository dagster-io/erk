# Add Print Statement to First Python File

## Context

User requested adding a print statement to the first Python file found in the codebase.

The first file found is `src/erk/__init__.py`, which contains the CLI entry point module.

## Plan

**File to modify:** `src/erk/__init__.py`

Add a `print` statement at the top of the `main()` function:

```python
def main() -> None:
    """CLI entry point used by the `erk` console script."""
    print("erk starting")
    cli()
```

## Verification

Run `erk --help` and verify "erk starting" is printed before the help output.
