# Plan: Disallow Dots in Branch and Worktree Names

## Problem

Branch name `1815-fix-.worker-impl-appearing-12-01-0442` was generated from an issue title containing `.worker-impl`. The dot character passes through sanitization, which violates git's refname rules: "no slash-separated component can begin with a dot".

## Root Cause

In `packages/erk-shared/src/erk_shared/naming.py`:

1. **Line 16**: `_SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._/-]+")` - allows `.`
2. **Line 106**: `sanitize_worktree_name()` uses `[^a-z0-9.-]+` - explicitly allows `.`
3. **Line 147**: `sanitize_branch_component()` uses `_SAFE_COMPONENT_RE` - allows `.`

Meanwhile, `derive_branch_name_from_title()` at line 490 correctly uses `[^a-z0-9-]` which excludes dots.

## Solution

Remove `.` from allowed characters in all branch/worktree sanitization functions:

### Changes to `packages/erk-shared/src/erk_shared/naming.py`

1. **Line 16**: Update `_SAFE_COMPONENT_RE` pattern
   ```python
   # Before
   _SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._/-]+")

   # After
   _SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9_/-]+")
   ```

2. **Line 106**: Update `sanitize_worktree_name()` regex
   ```python
   # Before
   replaced = re.sub(r"[^a-z0-9.-]+", "-", replaced_underscores)

   # After
   replaced = re.sub(r"[^a-z0-9-]+", "-", replaced_underscores)
   ```

3. **Update docstrings**: Change `[A-Za-z0-9.-]` → `[A-Za-z0-9-]` in:
   - `sanitize_worktree_name()` docstring (line 75)
   - `sanitize_branch_component()` docstring (line 124)

### Test Updates in `tests/core/utils/test_naming.py`

Add test cases to verify dots are replaced with hyphens:

```python
# For sanitize_worktree_name
(".worker-impl", "worker-impl"),
("fix-.worker", "fix-worker"),
("name.with.dots", "name-with-dots"),

# For sanitize_branch_component
(".hidden-file", "hidden-file"),
("file.extension", "file-extension"),
```

## Files to Modify

1. `packages/erk-shared/src/erk_shared/naming.py` - Core fix
2. `tests/core/utils/test_naming.py` - Add test cases

## Verification

Run tests after changes:
```bash
uv run pytest tests/core/utils/test_naming.py -v
```