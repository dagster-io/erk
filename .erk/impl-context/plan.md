# Plan: Add print statement to first Python file

## Context

User requested adding a print statement to the first Python file found in the project.

## Changes

**File:** `src/erk/__main__.py`

Add `print("hello")` at the top of the file (after the docstring, before imports):

```python
"""Allow erk to be run as a module: python -m erk."""

print("hello")

from erk import main

if __name__ == "__main__":
    main()
```

## Verification

Run `python -m erk` and confirm "hello" is printed.
