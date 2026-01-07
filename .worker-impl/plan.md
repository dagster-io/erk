# Plan: Fix `erk land -f` to Execute Objective Update

## Problem

When using `erk land -f` (force flag), the command merges the PR but then prints:
```
Run '/erk:objective-update-with-landed-pr --pr N --objective M --branch X --auto-close' to update objective
```

Instead of actually running the command. The `--force` flag should mean "skip prompts and do it", not "skip prompts and tell me what to do manually".

## Solution

Modify `prompt_objective_update()` in `objective_helpers.py` to execute the Claude command when `force=True`, just like it does when the user confirms interactively.

## Files to Modify

### 1. `src/erk/cli/commands/objective_helpers.py`

**Current code (lines 187-190):**
```python
if force:
    # --force skips all prompts, print command for later
    user_output(f"   Run '{cmd}' to update objective")
    return
```

**New code:**
```python
if force:
    # --force skips prompt but still executes the update
    user_output("")
    user_output("Starting objective update...")

    result = stream_command_with_feedback(
        executor=ctx.claude_executor,
        command=cmd,
        worktree_path=repo_root,
        dangerous=True,
    )

    if result.success:
        user_output("")
        user_output(click.style("✓", fg="green") + " Objective updated successfully")
    else:
        user_output("")
        user_output(
            click.style("⚠", fg="yellow") + f" Objective update failed: {result.error_message}"
        )
        user_output("  Run '/erk:objective-update-with-landed-pr' manually to retry")
    return
```

### 2. `tests/commands/land/test_objective_update.py`

Update `test_land_force_skips_objective_update_prompt()`:

- Rename to `test_land_force_runs_objective_update_without_prompt()`
- Update docstring to reflect new behavior
- Change assertion from `len(executor.executed_commands) == 0` to `== 1`
- Add assertions for correct command arguments and success output

## Test Plan

1. Run `uv run pytest tests/commands/land/test_objective_update.py` to verify all tests pass
2. Manual verification: `erk land -f` on a PR linked to an objective should execute the update and block until complete