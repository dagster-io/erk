---
steps:
  - name: "Update constants in common.py"
  - name: "Rename function in diagnostics.py"
  - name: "Update docstrings in source files"
  - name: "Update placeholder branch patterns"
  - name: "Update test files"
  - name: "Run tests"
---

# Plan: Standardize "slot" Terminology for Worktree Pool

**Replaces:** [#4381](https://github.com/dagster-io/erk/issues/4381)

## Goal

Use "slot" terminology consistently for worktree pool. Change directory names from `erk-managed-wt-XX` to `erk-slot-XX` and placeholder branches from `__erk-slot-XX-placeholder__` to `__erk-slot-XX-br-stub__`.

## Naming Convention

| Thing | Old | New |
|-------|-----|-----|
| Worktree dir | `erk-managed-wt-XX` | `erk-slot-XX` |
| Placeholder branch | `__erk-slot-XX-placeholder__` | `__erk-slot-XX-br-stub__` |

## Current State (verified against master)

- `SLOT_NAME_PREFIX = "erk-managed-wt"` in `src/erk/cli/commands/slot/common.py:14`
- `get_placeholder_branch_name()` returns `__erk-slot-{number}-placeholder__`
- `_find_erk_managed_dirs` function in `src/erk/cli/commands/slot/diagnostics.py:32`
- 30 files total contain "erk-managed-wt" (4 source, 26 test)
- 36 occurrences of placeholder pattern across 10 files

## Scope Clarification

**KEEP "erk-managed"** (refers to bundled artifacts, NOT worktree pool):
- `src/erk/artifacts/*.py` - `is_erk_managed()`, workflow/hook syncing
- `src/erk/cli/commands/artifact/*.py` - artifact management
- Hook scripts - "erk-managed projects" scope checks

**CHANGE to "slot"** (refers to worktree pool):
- Directory names, placeholder branches, function names, user output

## Implementation Steps

### Step 1: Update constants in common.py
**File:** `src/erk/cli/commands/slot/common.py`

```python
# Line 14: Change
SLOT_NAME_PREFIX = "erk-managed-wt"
# To
SLOT_NAME_PREFIX = "erk-slot"
```

Update `get_placeholder_branch_name()` (~line 46):
```python
return f"__erk-slot-{slot_number}-br-stub__"
```

Update `is_placeholder_branch()` regex:
```python
return bool(re.match(r"^__erk-slot-\d+-br-stub__$", branch_name))
```

Update docstrings to reflect new patterns.

### Step 2: Rename function in diagnostics.py
**File:** `src/erk/cli/commands/slot/diagnostics.py`

- Rename `_find_erk_managed_dirs` → `_find_slot_dirs`
- Update docstrings (pattern `erk-managed-wt-*` → `erk-slot-*`)

### Step 3: Update docstrings in source files
Global find-replace `erk-managed-wt` → `erk-slot` in:
- `src/erk/cli/commands/slot/common.py`
- `src/erk/cli/commands/slot/diagnostics.py`
- `src/erk/cli/commands/slot/unassign_cmd.py`
- `src/erk/cli/commands/slot/list_cmd.py`
- `src/erk/core/worktree_pool.py`
- `src/erk/cli/commands/exec/scripts/slot_objective.py`
- `src/erk/cli/shell_utils.py` (line 63: "erk-managed worktrees" → "pool slots")
- `.claude/commands/erk/objective-next-plan.md` (line 41)

### Step 4: Update placeholder branch patterns
Global find-replace `placeholder__` → `br-stub__` for branch patterns in:
- `src/erk/cli/commands/slot/common.py`
- All test files that reference `__erk-slot-XX-placeholder__`

### Step 5: Update all test files (~26 files)
Search for `erk-managed-wt` and `placeholder__` in tests/ and update:
- Test fixtures and assertions with hardcoded slot names
- Expected placeholder branch names

### Step 6: Run tests
Verify all tests pass with devrun agent.

## Execution Approach

1. Update constants in `common.py` (source of truth)
2. Global find-replace: `erk-managed-wt` → `erk-slot` (careful with "erk-managed" for artifacts)
3. Global find-replace: `-placeholder__` → `-br-stub__` (only for branch patterns)
4. Rename function: `_find_erk_managed_dirs` → `_find_slot_dirs`
5. Run tests, fix any remaining issues

## Notes

- Clean break - no migration for existing worktrees (user must re-init pool)
- Do NOT touch "erk-managed" references in artifact code