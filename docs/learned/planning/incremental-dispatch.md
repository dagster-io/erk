---
title: Incremental Dispatch System
read_when:
  - "dispatching a local plan against an existing PR"
  - "working with incremental dispatch workflow"
  - "understanding commit-level vs PR-level plan embedding"
tripwires:
  - action: "dispatching a plan without an existing open PR"
    warning: "Incremental dispatch requires an OPEN PR (not draft). Unlike regular dispatch, it does not require the erk-plan label."
  - action: "modifying commit message format in incremental dispatch"
    warning: "The commit message embeds the full plan content in the body. This is intentional — it provides commit-level plan context in git history."
---

# Incremental Dispatch System

Dispatches a local plan against an existing PR for remote implementation, without requiring the erk-plan label.

## Implementation

**Source:** `src/erk/cli/commands/exec/scripts/incremental_dispatch.py`

## Two-Part Plan Embedding

Incremental dispatch embeds the plan at two levels:

1. **Commit-level** (local git history): The full plan content is embedded in the commit message body:

   ```
   Incremental dispatch for PR #<number>

   <full plan content>
   ```

   This preserves plan context in the git log for future reference.

2. **PR-level** (reviewer context): The plan is written to `.erk/impl-context/` files via `build_impl_context_files()`, making it available to the remote implementation agent.

## Worktree Index Sync

When the target branch is checked out in a worktree, incremental dispatch must keep the working tree in sync after the plumbing commit:

1. Detects if the branch is checked out via `git.worktree.is_branch_checked_out()`
2. Writes impl-context files to disk in the worktree
3. Stages files with `git.commit.stage_files(force=True)`

This ensures `git status` is clean after the plumbing commit advances the branch.

## Workflow Trigger

The dispatch triggers the plan-implement workflow with:

- `dispatch_type`: `"incremental"` (distinguishes from full dispatch)
- `plan_backend`: `"planned_pr"` (specifies the plan backend type)
- Additional inputs: `plan_id`, `submitted_by`, `plan_title`, `branch_name`, `pr_number`, `base_branch`

## Related Documentation

- [Impl-Context Staging Directory](impl-context.md) — how impl-context files are managed
- [PR Submission Patterns](pr-submission-patterns.md) — PR lifecycle context
