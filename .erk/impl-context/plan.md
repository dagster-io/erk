# Plan: Add print statement to `src/erk/__init__.py`

## Context

User requested adding a print statement to the first Python file found. The first file is `src/erk/__init__.py`.

## Change

Add `print("hello")` at the top of the `main()` function in `src/erk/__init__.py:10`.

```python
def main() -> None:
    """CLI entry point used by the `erk` console script."""
    print("hello")
    cli()
```

## Verification

Run `python -c "import erk"` to confirm no import errors.
