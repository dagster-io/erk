# Plan: Clarify land.sh deferred cleanup in confirmation messages

## Problem

The `erk land` command shows confirmation prompts that imply immediate action:
```
Unassign slot 'erk-slot-27' and delete branch 'P5903-...'? [Y/n]:
```

But the cleanup only happens when the user sources the generated `land.sh` script, not immediately. This is confusing.

## Solution

Update the three confirmation messages in `_gather_cleanup_confirmation` to indicate the action is deferred until `land.sh` executes.

## Changes

**File:** `src/erk/cli/commands/land_cmd.py`

### 1. SLOT_ASSIGNED case (line 226-228)
```python
# Before:
f"Unassign slot '{resolved.assignment.slot_name}' "
f"and delete branch '{target.branch}'?",

# After:
f"After landing, unassign slot '{resolved.assignment.slot_name}' "
f"and delete branch '{target.branch}'?",
```

### 2. SLOT_UNASSIGNED case (line 239-242)
```python
# Before:
f"Release slot '{target.worktree_path.name}' and delete branch '{target.branch}'?",

# After:
f"After landing, release slot '{target.worktree_path.name}' and delete branch '{target.branch}'?",
```

### 3. NON_SLOT case (line 244-246)
```python
# Before:
f"Delete branch '{target.branch}'? (worktree preserved)",

# After:
f"After landing, delete branch '{target.branch}'? (worktree preserved)",
```

## Verification

1. Run `erk land` in a slot worktree and verify the confirmation message now starts with "After landing,"
2. Confirm the flow still works correctly (confirmation → script output → script execution performs cleanup)