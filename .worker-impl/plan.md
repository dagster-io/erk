# Plan: Make kwargs required on `build_blocking_message`

## Summary

Add `*` to `build_blocking_message` function signature to require keyword arguments, then update all call sites.

## Files to Modify

1. `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` - Function definition + production call
2. `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py` - Test call sites

## Implementation Steps

### Step 1: Update function signature (exit_plan_mode_hook.py:223)

Change from:
```python
def build_blocking_message(
    session_id: str,
    current_branch: str | None,
    ...
) -> str:
```

To:
```python
def build_blocking_message(
    *,
    session_id: str,
    current_branch: str | None,
    ...
) -> str:
```

### Step 2: Update production call site (exit_plan_mode_hook.py:419-427)

Convert positional args to keyword args:
```python
build_blocking_message(
    session_id=hook_input.session_id,
    current_branch=hook_input.current_branch,
    plan_file_path=hook_input.plan_file_path,
    objective_issue=hook_input.objective_issue,
    plan_title=hook_input.plan_title,
    worktree_name=hook_input.worktree_name,
    pr_number=hook_input.pr_number,
    plan_issue_number=hook_input.plan_issue_number,
    editor=hook_input.editor,
)
```

### Step 3: Update test call sites (test_exit_plan_mode_hook.py)

Update all calls in `TestBuildBlockingMessage` class (~14 calls) to use keyword arguments.

## Verification

Run tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py -v`