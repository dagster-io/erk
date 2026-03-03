# Fix: Hide "Create a plan PR on the current branch" when on trunk

## Context

When a user completes plan mode while on `master` (or `main`), the exit-plan-mode hook presents "Create a plan PR on the current branch" as an option. This shouldn't be offered because creating a PR on the trunk branch is nonsensical — PRs merge *into* trunk, and the project rules explicitly forbid committing directly to master.

The existing code already has a warning for being on trunk (lines 359-367), but the option visibility check only considers `branch_has_commits`, not whether the branch *is* trunk.

## Changes

### 1. `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py`

Two conditions need the same fix — add a trunk branch check:

**Line 342** (option display):
```python
# Before
if not branch_has_commits:

# After
if not branch_has_commits and current_branch not in ("master", "main"):
```

**Line 381** (instruction block for the option):
```python
# Before
if not branch_has_commits:

# After
if not branch_has_commits and current_branch not in ("master", "main"):
```

### 2. `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`

Add a test case:

```python
def test_current_branch_option_hidden_on_trunk(self) -> None:
    """Option 'Create a plan PR on the current branch' hidden when on master."""
    plan_path = Path("/home/user/.claude/plans/session-123.md")
    message = build_blocking_message(
        session_id="session-123",
        current_branch="master",
        branch_has_commits=False,
        plan_file_path=plan_path,
        plan_title=None,
        worktree_name=None,
        pr_number=None,
        plan_number=None,
        editor=None,
    )
    assert "Create a plan PR on the current branch" not in message
    assert "/erk:plan-save --current-branch" not in message
    # Other options should still be present
    assert "Create a plan PR on new branch" in message
    assert "Just implement on the current branch without creating a PR." in message
```

## Verification

1. Run unit tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`
2. Verify existing tests still pass (the `test_current_branch_option_shown_when_no_commits` test uses `current_branch="feature-branch"`, so it won't be affected)
