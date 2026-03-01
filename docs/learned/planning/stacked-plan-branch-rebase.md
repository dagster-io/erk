---
title: Stacked Plan Branch Rebase
read_when:
  - "working with stacked plans that have non-trunk parents"
  - "debugging gt track failures for plan branches"
  - "understanding how plan branches integrate with Graphite stacking"
tripwires:
  - action: "calling gt track before rebasing a stacked plan branch"
    warning: "Always rebase BEFORE gt track for stacked plans (not after). gt track requires the parent branch to be an ancestor in git history."
  - action: "rebasing a plan branch when parent is trunk"
    warning: "Only rebase when parent != trunk. Trunk parents are always correctly based and don't need rebase."
---

# Stacked Plan Branch Rebase

When a plan is stacked on a non-trunk parent branch, the parent may have advanced since the plan was saved. `_rebase_and_track_for_plan()` rebases the plan branch onto the parent's current tip before Graphite tracking.

## Problem

`gt track` requires the parent branch to be an ancestor in git history for proper stacking. If the parent has advanced since the plan was created, the plan branch's history doesn't include the parent's tip, and `gt track` fails or creates incorrect stacking relationships.

## Solution

<!-- Source: src/erk/cli/commands/branch/checkout_cmd.py, _rebase_and_track_for_plan -->

`_rebase_and_track_for_plan()` handles this in two steps:

1. **Rebase** (only when `parent_branch != trunk`): Rebase onto `origin/{parent_branch}` to include the parent's current tip in history
2. **Track**: Register the branch with Graphite via `track_branch(repo_root, branch, parent_branch)`

For trunk-parented plans, the function skips the rebase (trunk is always a valid ancestor) and proceeds directly to tracking.

## Parent Branch Detection

The parent is determined from plan metadata (`base_ref_name`), not guessed. If the metadata value is a string, it's used as the parent; otherwise defaults to trunk. This metadata is set at plan creation time (by `plan-save` via the draft PR's base ref), ensuring plans remember their stacking relationship across sessions.

## Error Handling

When the rebase encounters conflicts:

1. Rebase is aborted: `ctx.git.rebase.rebase_abort(worktree_path)`
2. User is warned with a recovery command: `cd {worktree_path} && git rebase origin/{parent_branch}`
3. Execution continues (worktree is still created and available)
4. Branch tracking is still registered

The function does not exit on conflict, the worktree remains usable for manual resolution.

## Local Branch Fetch

Before rebasing, the function follows the LBYL pattern: it checks `list_local_branches()` for the parent, and only if absent, fetches from origin and creates a tracking branch. This avoids unnecessary network calls when the branch already exists locally.

## Integration Points

The function is called at three points in `erk br co --for-plan`:

| Context                  | When                                           |
| ------------------------ | ---------------------------------------------- |
| Stack-in-place           | Current worktree already assigned to pool slot |
| Single worktree match    | Exactly one worktree contains the branch       |
| Multi-worktree selection | Multiple worktrees, one has direct checkout    |

All three follow the same sequence: `_rebase_and_track_for_plan()` -> `_setup_impl_for_plan()` -> `_perform_checkout()`.

## Mirror Pattern

This implementation mirrors the stacked PR checkout pattern in `_checkout_pr()` in `pr/checkout_cmd.py`, which performs the same rebase-before-track logic for stacked PRs. The key difference: plan checkout always calls `track_branch()` explicitly, while PR checkout handles tracking conditionally.

## Related Documentation

- [Planned PR Branch Sync](planned-pr-branch-sync.md) - How plan branches sync with remote
- [Planned PR Lifecycle](planned-pr-lifecycle.md) - PR body format and stage transitions
