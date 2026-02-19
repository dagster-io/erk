# Add Print Statement to First Python File

## Context

The user requested adding a print statement to the first Python file found in the codebase. The first file found is `src/erk/__init__.py`, which is the CLI entry point package.

## Implementation

Add a `print("hello")` statement to `src/erk/__init__.py:10` inside the `main()` function.

**File:** `src/erk/__init__.py`

**Change:**
```python
def main() -> None:
    """CLI entry point used by the `erk` console script."""
    print("hello")
    cli()
```

## Verification

Run `erk --help` and verify "hello" is printed before the help output.
