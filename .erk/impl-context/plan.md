# Add print statement to `src/erk/__main__.py`

## Context

User requested adding a print statement saying "for dgibson after plumbing" to the first Python file found. The first file alphabetically under `src/` is `src/erk/__main__.py`.

## Changes

### `src/erk/__main__.py`

Add `print("for dgibson after plumbing")` before the `if __name__` block:

```python
"""Allow erk to be run as a module: python -m erk."""

from erk import main

print("for dgibson after plumbing")

if __name__ == "__main__":
    main()
```

## Verification

- Run `python -m erk` and confirm the print statement appears
