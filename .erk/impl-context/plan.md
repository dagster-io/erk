# Add print statement to __main__.py

## Context

User wants to add a print statement saying "for dgibson after plubming" to the first Python file found in the project (`src/erk/__main__.py`).

## Change

In `src/erk/__main__.py`, add `print("for dgibson after plubming")` before the `main()` call.

**File:** `src/erk/__main__.py`

**Current:**
```python
if __name__ == "__main__":
    main()
```

**After:**
```python
if __name__ == "__main__":
    print("for dgibson after plubming")
    main()
```

## Verification

Run `python -m erk` and confirm "for dgibson after plubming" appears in stdout.
