# Fix inaccurate "dedicated worktree" copy in exit plan mode hook

## Context

The exit plan mode hook presents options via AskUserQuestion when a plan exists. Option 1 ("Create new branch and planned PR") gets embellished by Claude to say "for implementation in a dedicated worktree" — which is inaccurate. What actually happens is: a branch and draft PR are created (a "planned PR"), and the user decides what to do with it afterward (implement locally, dispatch remotely, etc.).

The inaccuracy has two sources:
1. The option 1 description doesn't clearly state the user decides next steps
2. The trunk warning (line 412) explicitly mentions "dedicated worktree", which Claude picks up

## Changes

**File:** `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py`

### 1. Update option 1 description (lines 385-388)

Current:
```python
f'  {option_num}. "Create new branch and planned PR. Stays on current branch."'
" - Create a new branch, save plan as draft PR."
```

New — make it clear a planned PR is created and user decides next:
```python
f'  {option_num}. "Create new branch and planned PR"'
" - Save plan as a draft PR on a new branch. You stay on your current branch."
```

### 2. Update trunk warning (lines 406-413)

Current:
```
Consider saving the plan and implementing in a dedicated worktree instead.
```

New — remove "dedicated worktree" reference:
```
Consider saving the plan as a PR first.
```

**File:** `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`

### 3. Update test assertions

- Line 487: Change `"dedicated worktree"` assertion to match new warning text
- Lines 845, 971: Update quoted option text to match new format (remove `. Stays on current branch.` from the quoted label)

## Verification

- Run unit tests: `pytest tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`
- Run ty/ruff on the changed files
