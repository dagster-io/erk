# Simplify current-wt implement commands to drop unnecessary `source`/`--script`

## Context

The plan-save next-steps output shows `source "$(erk br co --for-plan N --script)" && erk implement` for both "In current wt" and "In new wt" variants. The `source`/`--script` pattern is only needed when the command changes the shell's working directory (i.e., `--new-slot` creating a new worktree). For the current worktree case, the user is already in the right directory, so the simpler `erk br co --for-plan N && erk implement` suffices — consistent with how "Checkout plan: In current wt" already uses the non-source form.

## Changes

### 1. `packages/erk-shared/src/erk_shared/output/next_steps.py`

Change `implement_current_wt` property (line 35):
- From: `source "$(erk br co --for-plan {N} --script)" && erk implement`
- To: `erk br co --for-plan {N} && erk implement`

Change `implement_current_wt_dangerous` property (line 39):
- From: `source "$(erk br co --for-plan {N} --script)" && erk implement -d`
- To: `erk br co --for-plan {N} && erk implement -d`

Leave `implement_new_wt` and `implement_new_wt_dangerous` unchanged — they need `source`/`--script` because `--new-slot` creates a new worktree.

### 2. Tests — update expected strings

**`packages/erk-shared/tests/unit/output/test_next_steps.py`:**
- `test_plan_next_steps_implement_current_wt` (line 43)
- `test_plan_next_steps_implement_current_wt_dangerous` (lines 49-51)

**`tests/unit/shared/test_next_steps.py`:**
- `test_implement_current_wt` (lines 43-44)
- `test_implement_current_wt_dangerous` (lines 52-53)

### 3. Documentation — update `docs/learned/planning/next-steps-output.md`

Update the "Shell Activation Pattern" section (line 34) to clarify that only the `new_wt` variants use the `source "$()"` pattern, since current-wt commands don't change directories.

## Verification

- Run unit tests: `uv run pytest packages/erk-shared/tests/unit/output/test_next_steps.py tests/unit/shared/test_next_steps.py -v`
- Visually confirm `format_plan_next_steps_plain()` output looks correct with simplified current-wt commands
