# Fix: `erk br co --for-plan` output to include activation instructions

## Context

When running `erk br co --for-plan <number>` in non-script mode, the command outputs the plan setup messages but does **not** print the activation/source instructions that tell the user how to activate the worktree environment. By contrast, running `erk br co <branch>` (without `--for-plan`) correctly prints the activation instructions:

```
To activate the worktree environment:
  source /path/to/.erk/bin/activate.sh  (copied to clipboard)
```

The user expects both commands to show the activation instructions since both result in a worktree switch.

## Root Cause Analysis

The `--for-plan` path in `branch_checkout()` (checkout_cmd.py) has the same code structure as the regular checkout path — both eventually call `_perform_checkout()` which should print activation instructions. However, the user has observed that the activation instructions are missing after `--for-plan` checkout.

The most likely root cause is that `_perform_checkout()` encounters a problem in `display_sync_status()` or `ensure_worktree_activate_script()` for newly-created tracking branches. Specifically, `display_sync_status()` calls `ctx.git.branch.get_ahead_behind()` which may raise an unhandled exception for branches that were just created with `create_tracking_branch()` but haven't been fully fetched, causing the remaining output (activation instructions) to be skipped.

Regardless of the exact failure mode, the fix should ensure activation instructions are always printed after `--for-plan` checkout, and add a test that explicitly verifies this.

## Changes

### File 1: `src/erk/cli/commands/branch/checkout_cmd.py`

**Ensure activation instructions are printed for `--for-plan` checkout.**

In `_perform_checkout()`, wrap `display_sync_status()` in a try/except so that sync status errors don't prevent activation instructions from being printed:

```python
if should_output_message:
    user_output(user_message)
    # Display sync status after checkout message (non-critical)
    try:
        display_sync_status(ctx, worktree_path=target_path, branch=branch, script=script)
    except Exception:
        pass  # Sync status is informational, don't block activation output

    # Print activation instructions for opt-in workflow
    activation_script_path = ensure_worktree_activate_script(
        worktree_path=target_path,
        post_create_commands=None,
    )
    print_activation_instructions(
        activation_script_path,
        source_branch=None,
        force=False,
        config=activation_config_activate_only(),
        copy=True,
    )
```

### File 2: `tests/commands/branch/test_checkout_cmd.py`

**Add test that verifies `--for-plan` checkout prints activation instructions.**

Add a new test `test_checkout_for_plan_prints_activation_instructions()` that:

1. Sets up the standard test environment with a plan
2. Runs `erk br co --for-plan <number>` (non-script mode)
3. Asserts that the output contains:
   - `"Created .impl/ folder from plan #"` (existing assertion)
   - `"To activate the worktree environment:"` (new assertion)
   - `"source "` and `"activate.sh"` (new assertion verifying the source command)

The test should be placed right after the existing `test_checkout_for_plan_creates_impl_folder()` test at line ~685.

Also update the existing `test_checkout_for_plan_creates_impl_folder()` to verify activation output is present.

### File 3: `tests/commands/branch/test_checkout_cmd.py` (additional test)

**Add test for `--for-plan` in stack-in-place path (non-script mode).**

Add a test `test_checkout_stacks_in_place_for_plan_prints_activation()` that verifies when `--for-plan` is used and the current worktree is a pool slot (stack-in-place path, lines 519-565 of checkout_cmd.py), the activation instructions are still printed. This covers the other `--for-plan` code path where `_setup_impl_for_plan` and `_perform_checkout` are called from within the stack-in-place block.

## Files NOT Changing

- `src/erk/cli/activation.py` — The activation script generation and printing functions work correctly. The issue is in the caller not reaching them.
- `src/erk/cli/commands/checkout_helpers.py` — The `navigate_to_worktree` and `display_sync_status` functions are fine. The fix is in how they're called.
- `src/erk/cli/commands/navigation_helpers.py` — Not involved in `--for-plan` flow.
- Any `--script` mode paths — Script mode already works correctly (the `_setup_impl_for_plan` function correctly generates activation scripts in script mode).

## Implementation Details

### Key Code Patterns

- `user_output()` → routes to stderr (visible to user)
- `machine_output()` → routes to stdout (for shell integration)
- `print_activation_instructions()` → uses `user_output()` for instructions, `copy_to_clipboard_osc52()` for clipboard
- `ensure_worktree_activate_script()` → idempotent, creates `.erk/bin/activate.sh` if missing

### Edge Cases

1. **Newly created tracking branch**: When `--for-plan` creates a tracking branch from origin, `get_ahead_behind()` may fail because the upstream tracking ref isn't fully set up. The fix wraps this in a try/except.
2. **Stack-in-place path**: When the user is already in a pool slot, `--for-plan` takes the stack-in-place path (lines 519-565). This also calls `_perform_checkout` and should get the same fix.
3. **No worktree activation script**: `ensure_worktree_activate_script()` handles this by creating the script if missing.

### Test Environment Setup

The tests use:
- `CliRunner` from Click for CLI invocation
- `FakeGit` for git operation mocking
- `erk_isolated_fs_env` for temporary filesystem
- `build_workspace_test_context` for constructing test context

The existing test `test_checkout_for_plan_creates_impl_folder` at line 685 provides the exact test setup pattern to follow.

## Verification

1. Run the existing test suite for branch checkout: `pytest tests/commands/branch/test_checkout_cmd.py -v`
2. Verify the new test passes and checks for activation instructions in output
3. Run `ty` for type checking
4. Run `ruff check` for linting