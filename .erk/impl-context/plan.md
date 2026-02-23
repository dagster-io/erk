# Plan: Add Print Statement to First Python File

## Context

The user requested adding a print statement to the first Python file found in the project. The first file found is `src/erk/__init__.py`, the package entry point.

## Change

Add a print statement to `/Users/schrockn/code/erk/src/erk/__init__.py`.

**File:** `src/erk/__init__.py`

Add `print("hello")` after the module docstring, before the import:

```python
"""erk CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `erk --help` for details.
"""

print("hello")

from erk.cli.cli import cli
...
```

## Verification

Run `python -c "import erk"` and confirm `hello` is printed.
