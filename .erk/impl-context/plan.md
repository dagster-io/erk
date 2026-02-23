# Add Print Statement to First Python File

## Context

User requested adding a print statement to the first Python file found in the codebase.

## Target File

`src/erk/__init__.py` — the first Python file found (sorted by modification time) in the `src/` directory.

Current content:
```python
"""erk CLI entry point."""

from erk.cli.cli import cli


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
```

## Change

Add a `print("hello")` statement at the top of the `main()` function body.

## Implementation

Edit `src/erk/__init__.py:10-12`:

```python
def main() -> None:
    """CLI entry point used by the `erk` console script."""
    print("hello")
    cli()
```

## Verification

Run `python -c "from erk import main"` to confirm the file is importable, and `erk --help` to confirm the print fires on invocation.
