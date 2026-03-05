# Add print statement to __main__.py

## Context
User requested adding a print statement saying "for dgibson after plubming" to the first Python file found. The first file by modification time is `src/erk/__main__.py`.

## Change

File: `src/erk/__main__.py`

Add `print("for dgibson after plubming")` before the `main()` call:

```python
"""Allow erk to be run as a module: python -m erk."""

from erk import main

if __name__ == "__main__":
    print("for dgibson after plubming")
    main()
```

## Verification

Run `python -m erk` and confirm the print statement appears before normal output.
