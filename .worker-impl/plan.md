# Fix: Skip learn prompt for remote PRs in `erk land`

## Problem

When running `erk land <url>` on a remote PR, the command incorrectly prompts:

```
Warning: Plan #4867 has not been learned from.
Continue landing without learning? [y/n]:
```

This prompt should only appear for PRs that have a local worktree, since the "learn" feature extracts insights from local Claude sessions.

## Root Cause

In `_land_specific_pr()` (land_cmd.py:900-905), the learn check runs unconditionally based on the branch name matching a plan pattern, without checking whether a local worktree exists.

The code at line 870 already determines `worktree_path`:
```python
worktree_path = ctx.git.find_worktree_for_branch(main_repo_root, branch)
```

But this information isn't used to gate the learn check.

## Fix

Modify the condition at lines 900-905 from:
```python
plan_issue_number = extract_leading_issue_number(branch)
if plan_issue_number is not None:
    _check_learn_status_and_prompt(...)
```

To:
```python
plan_issue_number = extract_leading_issue_number(branch)
if plan_issue_number is not None and worktree_path is not None:
    _check_learn_status_and_prompt(...)
```

**File to modify:** `src/erk/cli/commands/land_cmd.py:900-905`

## Rationale

- If `worktree_path is None`: The PR is "remote only" - there's no local worktree with Claude sessions to learn from
- If `worktree_path is not None`: The PR has a local worktree, so learning check is meaningful

## Verification

1. Run `erk land <remote-pr-url>` for a PR without a local worktree - should NOT prompt about learning
2. Run `erk land` on a local plan branch that hasn't been learned from - should still prompt about learning