# Add print statement to first Python file

## Context

User requested adding a print statement to the first Python file found in the codebase.
The first Python file (by glob, sorted by modification time) is `src/erk/__init__.py`.

## Change

**File:** `src/erk/__init__.py`

Add `print("hello")` inside the `main()` function, before the `cli()` call:

```python
def main() -> None:
    """CLI entry point used by the `erk` console script."""
    print("hello")
    cli()
```

## Critical files

- `src/erk/__init__.py`

## Verification

Run `erk --help` and confirm "hello" appears in the output.
