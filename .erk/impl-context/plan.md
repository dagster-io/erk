# Add print("hello world") to src/erk/__init__.py

## Context

The prompt asks to put a `print("hello world")` in the first Python file found. The first Python file in the source tree is `src/erk/__init__.py`, which is the package's entry point module.

## Changes

### File: `src/erk/__init__.py`

Add `print("hello world")` as a top-level statement at the end of the module, after the existing `main()` function definition.

**Current contents:**

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

**After modification:**

```python
"""erk CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `erk --help` for details.
"""

from erk.cli.cli import cli


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()


print("hello world")
```

The `print("hello world")` statement is added as a new top-level statement at the end of the file, after a blank line following the `main()` function.

## Files NOT Changing

- No other files are modified
- No tests are added (this is a trivial one-line change)
- CHANGELOG.md is not modified

## Verification

After making the change, verify:

1. The file has correct syntax: `python -c "import ast; ast.parse(open('src/erk/__init__.py').read())"`
2. Ruff passes: run ruff check on the file
3. The print statement executes when the module is imported: `python -c "import erk"` should print "hello world"
