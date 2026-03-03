# Add Hello World Print Statement

## Context

User requested adding a hello world print statement to the first Python file found in the project.

The first project Python file (sorted by modification time from `src/erk/`) is `src/erk/__main__.py`.

## Plan

Add `print("Hello, World!")` as the first statement inside the `if __name__ == "__main__":` block in `src/erk/__main__.py`.

### File to Modify

`src/erk/__main__.py` (currently 7 lines)

### Change

```python
"""Allow erk to be run as a module: python -m erk."""

from erk import main

if __name__ == "__main__":
    print("Hello, World!")  # <-- add this line
    main()
```

## Verification

Run `python -m erk` and observe "Hello, World!" printed to stdout before normal erk output.
