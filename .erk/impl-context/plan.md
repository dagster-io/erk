# Fix: `erk br co --for-plan --script` doesn't checkout branch in stack-in-place path

## Context

When running `source "$(erk br co --for-plan 7955 --script)"` from a worktree that already has a slot assignment, the command reports success ("Stacked ... in place") but the branch never actually changes. The pool assignment is updated and `.impl/` is created, but the worktree stays on the old branch.

**Root cause**: In the stack-in-place path (line 529-567 of `checkout_cmd.py`), `_setup_impl_for_plan()` calls `sys.exit(0)` in script mode (line 326), which terminates the process before `_perform_checkout()` (line 558) can run `git checkout`.

## Fix

**File**: `src/erk/cli/commands/branch/checkout_cmd.py` (lines 529-567)

Move the git checkout to happen **before** `_setup_impl_for_plan()`:

1. Insert `ctx.branch_manager.checkout_branch(slot_result.worktree_path, branch)` after the pool assignment update but before the `_setup_impl_for_plan` call
2. Change `WorktreeInfo(branch=current_assignment.branch_name)` to `WorktreeInfo(branch=branch)` since checkout already happened

After the fix, `_perform_checkout` sees `need_checkout=False` and handles only navigation/activation — no double checkout.

## Test

**File**: `tests/commands/branch/test_checkout_cmd.py`

Add regression test `test_checkout_stacks_in_place_for_plan_with_script`:
- Set up pool state with CWD assigned to a slot on "old-branch"
- Invoke `["checkout", "--for-plan", "500", "--script"]`
- Assert the new branch was checked out (via `branch_manager.checked_out_branches`)
- Assert `.impl/` folder was created
- Assert exit code 0

Follow existing test patterns from `test_checkout_stacks_in_place_from_assigned_slot` (line 845) and `test_checkout_for_plan_creates_impl_folder` (line 685).

## Verification

1. `uv run pytest tests/commands/branch/test_checkout_cmd.py` — all existing tests pass, new test passes
2. `make fast-ci` — full CI green
