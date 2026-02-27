# Add print statement to second Python file

## Context

The prompt asks to "find the second Python file you find and add a print statement." The top-level directory of the repository contains three Python files in alphabetical order:

1. `clean_bad_tripwires.py`
2. `fix_tripwires.py` ← **second Python file**
3. `remove_tripwires.py`

The second Python file is `fix_tripwires.py`, a standalone script that converts tripwire entries from string list format to action/warning object format in YAML frontmatter.

## Changes

### File: `fix_tripwires.py`

Add a print statement at the top of the `main()` function (line 113), after the function definition.

**Current code (lines 112-115):**
```python
def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_tripwires.py <file1.md> [file2.md ...]")
        sys.exit(1)
```

**New code:**
```python
def main():
    print("Running fix_tripwires script")
    if len(sys.argv) < 2:
        print("Usage: python fix_tripwires.py <file1.md> [file2.md ...]")
        sys.exit(1)
```

The print statement `print("Running fix_tripwires script")` is added as the first line inside `main()`, before the argument check. This is a simple informational message that indicates the script has been invoked.

## Files NOT changing

- `clean_bad_tripwires.py` — first Python file, not the target
- `remove_tripwires.py` — third Python file, not the target
- All files under `src/`, `tests/`, `packages/`, etc. — out of scope

## Verification

1. Open `fix_tripwires.py` and confirm the print statement `print("Running fix_tripwires script")` is present as the first line of the `main()` function
2. Run `python fix_tripwires.py` with no arguments — should print "Running fix_tripwires script" followed by the usage message