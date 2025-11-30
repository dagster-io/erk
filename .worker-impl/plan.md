# Plan: Rename `.tmp` to `.erk/scratch` and Fix `/tmp` References

## Summary

Two related issues to fix:

1. The `/gt:pr-submit` command docs recommend writing PR body to `/tmp/pr-body-{uuid}.txt` instead of using the scratch infrastructure
2. The scratch directory `.tmp` should be renamed to `.erk/scratch` for clarity

## Changes Required

### 1. Rename `.tmp` → `.erk/scratch` in scratch module

**File:** `packages/erk-shared/src/erk_shared/scratch/scratch.py`

- Line 3: Update docstring from `.tmp/<session-id>/` to `.erk/scratch/<session-id>/`
- Line 37: Update docstring
- Line 44: Update docstring
- Line 49: Change `repo_root / ".tmp" / session_id` → `repo_root / ".erk" / "scratch" / session_id`
- Line 72: Update docstring example
- Line 105: Change `repo_root / ".tmp"` → `repo_root / ".erk" / "scratch"`

**File:** `packages/erk-shared/src/erk_shared/scratch/__init__.py`

- Line 3-4: Update docstring to mention `.erk/scratch/`

### 2. Update `.gitignore`

**File:** `.gitignore`

- Line 19: Change `.tmp/` → `.erk/scratch/`

### 3. Fix `/gt:pr-submit` command to use scratch infrastructure

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/commands/gt/pr-submit.md`

- Lines 43, 95-104: Update documentation to use `.erk/scratch/<session-id>/` instead of `/tmp`
- Update the recommendation to write PR body to `.erk/scratch/<session-id>/pr-body.txt`

### 4. Update tests

**File:** `packages/erk-shared/tests/unit/scratch/test_scratch.py`

- Update all assertions that check for `.tmp` path to use `.erk/scratch`
- Lines 22, 100, 109, etc.

**File:** `packages/dot-agent-kit/tests/unit/kits/gt/test_submit_branch.py`

- Line 490: Update assertion from `.tmp/test-session-123/` to `.erk/scratch/test-session-123/`

## Files to Modify

1. `packages/erk-shared/src/erk_shared/scratch/scratch.py`
2. `packages/erk-shared/src/erk_shared/scratch/__init__.py`
3. `.gitignore`
4. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/commands/gt/pr-submit.md`
5. `packages/erk-shared/tests/unit/scratch/test_scratch.py`
6. `packages/dot-agent-kit/tests/unit/kits/gt/test_submit_branch.py`

## Verification

- Run `uv run pytest packages/erk-shared/tests/unit/scratch/` to verify scratch module changes
- Run `uv run pytest packages/dot-agent-kit/tests/unit/kits/gt/test_submit_branch.py` to verify submit_branch changes
- Run `uv run pyright` for type checking
