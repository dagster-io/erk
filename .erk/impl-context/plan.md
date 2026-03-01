# Add a code comment to src/erk/__init__.py

## Context

This is a smoke-test task to verify the one-shot plan-and-implement pipeline works end-to-end. The goal is to add a single code comment to an existing file.

## Changes

### Modify: `src/erk/__init__.py`

Add a code comment above the `main()` function to clarify its role as the console script entry point.

**Current code (lines 10-12):**
```python
def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
```

**Target code:**
```python
# Entry point registered as console_scripts in pyproject.toml
def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
```

This adds a single-line comment above `main()` noting that this function is the one registered in `pyproject.toml`'s `[project.scripts]` section.

## Files NOT Changing

- No other files are modified
- No tests need to be added or updated
- CHANGELOG.md is not modified

## Verification

1. Run `ruff check src/erk/__init__.py` — should pass with no errors
2. Run `ty check src/erk/__init__.py` — should pass with no errors
3. Visually confirm the comment is present above the `main()` function