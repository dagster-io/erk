# Add print statement to `src/erk/__main__.py`

## Context

User requested adding a print statement to the first Python file found in the project.

## Change

**File:** `src/erk/__main__.py`

Add `print("for dgibson after plubming")` at the top of the file (after the docstring/imports, before the `if __name__` block).

## Verification

Run `python -m erk` and confirm the print statement appears in output.
