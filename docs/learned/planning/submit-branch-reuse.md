---
title: Branch Reuse in Plan Submit
read_when:
  - "understanding branch reuse detection in submit"
  - "debugging branch conflicts in plan submit"
  - "implementing branch reuse prompts"
tripwires:
  - action: "implementing branch reuse detection in plan submit"
    warning: "When reusing existing branches, ensure Graphite tracking sync via BranchManager. Existing local branches may not be tracked in Graphite."
---

# Branch Reuse in Plan Submit

When submitting a plan for remote implementation, erk detects if local branches already exist for the issue and offers to reuse them. This prevents duplicate branches and preserves work in progress.

## Detection Mechanism

The `_find_existing_branches_for_issue()` function searches for branches matching `P{issue_number}-*`:

```python
def _find_existing_branches_for_issue(
    ctx: ErkContext,
    repo_root: Path,
    issue_number: int,
) -> list[str]:
    """Find local branches matching P{issue_number}-* pattern."""
    local_branches = ctx.git.list_local_branches(repo_root)
    prefix = f"P{issue_number}-"
    return sorted([b for b in local_branches if b.startswith(prefix)])
```

This returns branches sorted alphabetically. Since branch names include timestamps (e.g., `P123-feature-01-23-0909`), the last item is typically the most recent.

## User Interaction Flow

When existing branches are found:

```
Found existing local branch(es) for this issue:
  * P123-implement-feature-x-01-23-0909
  * P123-implement-feature-x-01-23-1015

New branch would be: P123-implement-feature-x-01-24-1400

Use existing branch 'P123-implement-feature-x-01-23-1015'? [Y/n]:
```

**Options:**

1. **Yes (default)**: Reuse the newest existing branch
2. **No + Delete**: Delete existing branches and create new
3. **No + Abort**: Cancel the operation

## Graphite Tracking Synchronization

**Critical**: When reusing an existing local branch, it may not be tracked in Graphite. The submit command ensures tracking via `BranchManager`:

```python
# After selecting existing branch
ctx.branch_manager.checkout_branch(repo_root, branch_to_use)
# BranchManager.checkout_branch handles Graphite tracking internally
```

For new branches, `BranchManager.create_branch()` handles both git branch creation and Graphite tracking automatically.

## Why Branch Reuse Matters

| Scenario                         | Without Reuse                  | With Reuse              |
| -------------------------------- | ------------------------------ | ----------------------- |
| Interrupted implementation       | Creates duplicate branch       | Continues existing work |
| Re-submitting after failure      | Orphans previous branch        | Uses existing branch    |
| Multiple submit attempts         | Branch proliferation           | Single branch           |
| Previous work-in-progress exists | Lost unless manually recovered | Preserved               |

## Implementation Location

See `src/erk/cli/commands/submit.py`:

- `_find_existing_branches_for_issue()` - Detection
- `_prompt_existing_branch_action()` - User interaction

## Related Documentation

- [Plan Lifecycle](lifecycle.md) - Full submit workflow context
- [Git and Graphite Edge Cases](../architecture/git-graphite-quirks.md) - Graphite tracking quirks
