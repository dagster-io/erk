# Add Hello World to src/erk/__init__.py

## Context

The task is to add a "hello world" message to the first Python file in the project. The first Python file found in the source tree is `src/erk/__init__.py`, which serves as the erk package's entry point module.

## Changes

### Modify: `src/erk/__init__.py`

Add a `print("hello world")` statement at the top of the module, after the docstring and before the import.

**Current content:**
```python
"""erk CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `erk --help` for details.
"""

from erk.cli.cli import cli


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
```

**New content:**
```python
"""erk CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `erk --help` for details.
"""

print("hello world")

from erk.cli.cli import cli


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
```

The only change is adding `print("hello world")` on line 8, after the module docstring and before the import statement.

## Files NOT Changing

- All other files in the project remain unchanged
- No test files are modified or created
- No configuration files are modified

## Implementation Details

- The `print("hello world")` is placed after the docstring but before imports, so it executes when the module is first imported
- This is a single-line addition with no dependencies or edge cases

## Verification

After implementation, verify by running:
```bash
python -c "import erk"
```
This should print `hello world` to stdout.