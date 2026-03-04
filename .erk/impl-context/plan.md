# Add "for dgibson" print statement

## Context

The user wants a `print("for dgibson")` statement added to the first Python source file found in the project. This was previously implemented and reverted; now it should be planned before implementation.

## Target File

`src/erk/__main__.py` — the first Python file in `src/` (by modification time).

## Change

Add `print("for dgibson")` inside the `if __name__ == "__main__":` block, before the `main()` call.

**Before:**
```python
if __name__ == "__main__":
    main()
```

**After:**
```python
if __name__ == "__main__":
    print("for dgibson")
    main()
```

## Verification

Run `python -m erk` and confirm `for dgibson` is printed to stdout before any other output.
