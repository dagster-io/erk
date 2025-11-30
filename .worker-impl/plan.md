# Plan: Fix duplicate checkout/co commands in `erk pr` help

## Problem

Running `erk pr` shows `checkout` and `co` as separate commands:

```
Commands:
  checkout  Checkout a pull request into a worktree.
  co        Checkout a pull request into a worktree.
  land      Land current PR and navigate to parent branch.
  submit    Submit current branch as a pull request.
```

Expected behavior (like `erk wt`): show them combined as `checkout, co`.

## Root Cause

The `pr_group` in `src/erk/cli/commands/pr/__init__.py` uses the default `click.Group`, which doesn't have alias deduplication logic. The `wt_group` correctly uses `cls=GroupedCommandGroup` which handles this.

## Solution

Change `pr_group` to use `GroupedCommandGroup`:

**File:** `src/erk/cli/commands/pr/__init__.py`

```python
# Before:
@click.group("pr")
def pr_group() -> None:

# After:
from erk.cli.help_formatter import GroupedCommandGroup

@click.group("pr", cls=GroupedCommandGroup)
def pr_group() -> None:
```

## Files to Modify

1. `src/erk/cli/commands/pr/__init__.py` - Add import and `cls=GroupedCommandGroup` parameter

## Verification

```bash
erk pr --help
```

Should show:
```
Commands:
  checkout, co  Checkout a pull request into a worktree.
  land          Land current PR and navigate to parent branch.
  submit        Submit current branch as a pull request.
```