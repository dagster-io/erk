# Plan: Add print statement to first Python file

## Context
User requested adding a print statement to the first Python file found in the project.

## Change
Add a `print()` statement to `src/erk/__init__.py` at the top of the `main()` function.

**File:** `src/erk/__init__.py`

```python
# Add before cli() call in main():
print("hello from erk")
```

## Verification
Run `python -c "from erk import main"` to confirm no import errors.
