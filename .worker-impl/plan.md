# Plan: Standardize "slot" Terminology for Worktree Pool

## Goal
Use "slot" terminology consistently for worktree pool. Keep "erk-managed" only for bundled artifacts.

## Naming Convention

| Thing | Old | New |
|-------|-----|-----|
| Worktree dir | `erk-managed-wt-XX` | `erk-slot-XX` |
| Placeholder branch | `__erk-slot-XX-placeholder__` | `__erk-slot-XX-br-stub__` |

## Scope Clarification

**KEEP "erk-managed"** (refers to bundled artifacts):
- `src/erk/artifacts/*.py` - `is_erk_managed()`, workflow/hook syncing
- `src/erk/cli/commands/artifact/*.py` - artifact management
- `src/erk/cli/commands/admin.py` - "erk-managed repository"
- Hook scripts - "erk-managed projects" scope checks

**CHANGE to "slot"** (refers to worktree pool):
- Directory names: `erk-managed-wt-XX` → `erk-slot-XX`
- Placeholder branches: `__erk-slot-XX-placeholder__` → `__erk-slot-XX-br-stub__`
- Functions: `_find_erk_managed_dirs` → `_find_slot_dirs`
- User output: "erk-managed" → "slots"

## Implementation

### Step 1: Update constants
**File:** `src/erk/cli/commands/slot/common.py`
```python
SLOT_NAME_PREFIX = "erk-slot"  # was "erk-managed-wt"
```
Also update `get_placeholder_branch_name()` to return `__erk-slot-XX-br-stub__`

### Step 2: Update placeholder branch pattern
**File:** `src/erk/cli/commands/slot/common.py`
- `get_placeholder_branch_name()`: return `f"__erk-slot-{slot_number}-br-stub__"`
- `is_placeholder_branch()`: update regex to match new pattern

### Step 3: Rename function in check_cmd.py
**File:** `src/erk/cli/commands/slot/check_cmd.py`
- Rename `_find_erk_managed_dirs` → `_find_slot_dirs`
- Update docstrings
- Line 268: Change user output from `"erk-managed"` to `"slots"`

### Step 4: Update docstrings/examples in slot commands
Replace `erk-managed-wt-XX` with `erk-slot-XX` in:
- `src/erk/cli/commands/slot/common.py`
- `src/erk/cli/commands/slot/check_cmd.py`
- `src/erk/cli/commands/slot/unassign_cmd.py`
- `src/erk/cli/commands/slot/list_cmd.py`
- `src/erk/core/worktree_pool.py`
- `src/erk/cli/commands/exec/scripts/slot_objective.py`
- `src/erk/cli/shell_utils.py` - "erk-managed worktrees" → "pool slots"
- `.claude/commands/erk/objective-next-plan.md`

### Step 5: Update all test files
~30 test files with hardcoded strings:
- `erk-managed-wt-XX` → `erk-slot-XX`
- `__erk-slot-XX-placeholder__` → `__erk-slot-XX-br-stub__`

### Step 6: Run tests
Verify all tests pass.

## Execution Approach
1. Update constants in `common.py`
2. Global find-replace: `erk-managed-wt` → `erk-slot`
3. Global find-replace: `placeholder__` → `br-stub__` (for the branch pattern)
4. Rename function: `_find_erk_managed_dirs` → `_find_slot_dirs`
5. Fix user output string (line 268 in check_cmd.py)
6. Run tests

## Notes
- Clean break - no migration for existing worktrees