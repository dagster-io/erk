# Add print statement to first Python file

## Context

User requested adding a print statement to the first Python file found in the project.

## Change

Add `print("hello")` at the top of `src/erk/__init__.py` (line 1, before the docstring).

## File

- `src/erk/__init__.py`

## Verification

Run `python -c "import erk"` and confirm "hello" is printed.
