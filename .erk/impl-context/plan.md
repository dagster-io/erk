# Add Print Statement to src/erk/__init__.py

## Context

User requested adding a print statement "for dgibson after plubming" to the first Python source file found in the project.

## File to Modify

`src/erk/__init__.py` — the first source file returned by glob, sorted by modification time.

## Change

Add `print("for dgibson after plubming")` as the first line of the `main()` function:

```python
def main() -> None:
    """CLI entry point used by the `erk` console script."""
    print("for dgibson after plubming")
    cli()
```

## Verification

Run `erk --help` and confirm the print statement appears before any CLI output.
