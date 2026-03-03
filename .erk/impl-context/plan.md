# Add Print Statement to First Python File

## Context

The user wants a print statement added to the first Python source file found in the project.

## Target File

`src/erk/__main__.py` — the entry point module that allows erk to be run as `python -m erk`.

## Change

Add `print("hello")` at the top of the module body, after the docstring and before the import.

### Current file (6 lines):
```python
"""Allow erk to be run as a module: python -m erk."""

from erk import main

if __name__ == "__main__":
    main()
```

### After change:
```python
"""Allow erk to be run as a module: python -m erk."""

print("hello")

from erk import main

if __name__ == "__main__":
    main()
```

## Critical File

- `src/erk/__main__.py`

## Verification

Run `python -m erk` and confirm `hello` is printed before normal output.
