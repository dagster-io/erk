---
title: Plan Save Branch Restoration
read_when:
  - "modifying plan_save.py branch checkout behavior"
  - "understanding try/finally patterns for git branch safety"
  - "working with temporary branch checkouts in erk"
tripwires:
  - action: "checking out a branch in plan_save without restoring the original"
    warning: "Plan save must always restore the original branch via try/finally. See plan-save-branch-restoration.md."
---

# Plan Save Branch Restoration

`plan_save.py` needs to temporarily checkout a branch to commit the plan file, then restore the original branch. This uses a try/finally pattern to guarantee restoration.

## Pattern

Located in `src/erk/cli/commands/exec/scripts/plan_save.py`, the `_save_as_draft_pr()` function:

<!-- Source: src/erk/cli/commands/exec/scripts/plan_save.py, _save_as_draft_pr -->

See `_save_as_draft_pr()` in `src/erk/cli/commands/exec/scripts/plan_save.py` — uses try/finally to guarantee branch restoration after temporary checkout for plan commit and push.

Key properties:

- Saves current branch name before checkout
- Creates plan branch from the same commit (no conflict with uncommitted work)
- Commits plan to `.erk/impl-context/plan.md`
- Pushes to origin with upstream tracking
- **Always** restores to `start_point` in the finally block, even if push fails

## Evolution

- PR #7491 removed checkout (plan committed without switching branches)
- PR #7494 re-added checkout with try/finally for the plan file commit step

## Testing

12 tests in `tests/unit/cli/commands/exec/scripts/test_plan_save.py`, including a dedicated `test_draft_pr_restores_original_branch` test that verifies:

- Two checkouts occur (plan branch, then back to original)
- The second checkout restores the exact original branch name

## Related Topics

- [Draft PR Plan Backend](../planning/draft-pr-plan-backend.md) - Backend that uses this pattern
