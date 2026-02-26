# Add Print Statement to __main__.py

## Context

User requested a print statement be added to the first Python file found in the project. The first file returned by glob is `src/erk/__main__.py`.

## Plan

Add a `print` statement to `/Users/schrockn/code/erk/src/erk/__main__.py`.

**Current file:**
```python
"""Allow erk to be run as a module: python -m erk."""

from erk import main

if __name__ == "__main__":
    main()
```

**Change:** Add `print("hello")` before the `main()` call.

**Target file:** `src/erk/__main__.py:5`

## Verification

Run `python -m erk` and confirm "hello" is printed before normal output.
