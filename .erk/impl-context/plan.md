# Plan: Add print statement to first Python file

## Context

User asked to add a print statement to the first Python file found.

## Changes

**File:** `src/erk/__main__.py`

Add `print("hello")` at the top of the file (after the docstring, before imports).

## Verification

Run `python -c "import ast; ast.parse(open('src/erk/__main__.py').read())"` to confirm valid syntax.
