---
title: Planned PR Branch Sync
read_when:
  - "implementing or debugging planned-PR plan setup"
  - "understanding branch sync during plan implementation"
  - "working with setup_impl_from_pr for planned PR plans"
  - "debugging divergence between local and remote plan branches"
tripwires:
  - action: "implementing planned-PR plan without syncing with remote"
    warning: "Before implementing a planned-PR plan, always sync with remote: fetch_branch -> checkout/create_tracking -> pull_rebase"
  - action: "detecting plan backend by checking backend type directly"
    warning: "Use github.get_pr() + pr_result.head_ref_name to discover the plan branch. There is only one backend (planned-PR)."
  - action: "creating a new branch for a planned-PR plan"
    warning: "Planned PR plans already have a branch created during plan-save. Reuse the existing branch, don't create a new one."
  - action: "committing to planned-PR plan branches after checkout without pulling remote"
    warning: "Both setup_impl_from_pr.py and submit.py use the same three-step sync: fetch_branch -> checkout/create_tracking -> pull_rebase. Skipping pull_rebase causes non-fast-forward push failures."
---

# Planned PR Branch Sync

When implementing a planned-PR plan, the local branch must be synced with remote because plan-save creates the branch and pushes it, then checks out the original branch. Remote may receive additional commits before implementation runs.

## The Problem

1. `plan_save` creates a branch, pushes it to remote, creates draft PR
2. `plan_save` checks out the original branch (user continues working)
3. Time passes (remote CI may add commits, user may re-plan)
4. `plan-implement` runs and needs the latest branch state

## Three-Step Sync Sequence

In `setup_impl_from_pr.py`, the sync follows this pattern:

```
fetch_branch → checkout/create_tracking → pull_rebase
```

### Step 1: Fetch Branch

<!-- Source: src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py, setup_impl_from_pr -->

Calls `git.remote.fetch_branch()` to fetch the named branch from origin, making remote state available locally.

### Step 2: Checkout or Create Tracking

Three possible states:

| State                 | Action                                                                                                 |
| --------------------- | ------------------------------------------------------------------------------------------------------ |
| Already on branch     | Skip checkout, proceed to pull                                                                         |
| Branch exists locally | `branch_manager.checkout_branch(cwd, branch_name)`                                                     |
| Branch only on remote | `branch_manager.create_tracking_branch(repo_root, branch_name, f"origin/{branch_name}")` then checkout |

### Step 3: Pull Rebase

<!-- Source: src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py, setup_impl_from_pr -->

Calls `git.remote.pull_rebase()` to fast-forward the local branch to remote HEAD. Only needed when already on branch or after checking out an existing local branch. Skip when creating a fresh tracking branch (already at remote HEAD).

## Backend Detection

The branch name is discovered via a lightweight GitHub PR query. Detection uses the PR's head ref:

<!-- Source: src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py -->

Calls `github.get_pr(repo_root, plan_number)` and reads `pr_result.head_ref_name` to discover the plan branch name. This is a planned-PR plan (reuse the existing branch and sync with remote).

## Idempotent Design

`setup-impl-from-pr` is safe to run multiple times:

- If already on the correct branch, it syncs with remote
- If branch exists locally, it checks out and syncs
- If branch only exists on remote, it creates tracking and checks out

This is why `plan-implement` always calls `setup-impl-from-pr` even when `.erk/impl-context/` already exists with plan tracking.

## Pattern Consistency: Setup and Submit

Both `setup_impl_from_pr.py` and `submit_pipeline.py` use an identical three-step sync pattern when working with draft-PR plan branches:

<!-- Source: src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py, setup_impl_from_pr -->
<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, push_and_create_pr -->

Both paths call the same three-step sequence: `fetch_branch()` → `create_tracking_branch()` / `checkout_branch()` → `pull_rebase()`. See the source files for exact call signatures.

PR #7697 added the missing `pull_rebase()` call to the submit path. Without it, the submit path would attempt to push commits onto a branch that had diverged from remote, causing non-fast-forward push failures.

## Legacy Branch Naming

Legacy plans used the `P{number}-{slugified-title}-{timestamp}` branch pattern. Current plans use the `plnd/` prefix.

## Auto-Force Push for Plan Implementation Branches

Plan implementation branches always diverge from remote because the draft PR scaffolding commits (from `plan-save`) differ from the worker's implementation commits. The PR submit pipeline auto-enables force-push for plan branches to avoid requiring `--force` every time.

**Detection:** `state.issue_number is not None` in `submit_pipeline.py`

**Derived flag:** `effective_force = state.force or is_plan_impl`

When auto-force activates, the pipeline prints a dim-styled informational message so the user understands why force-push occurred. See [Derived Flags Pattern](../architecture/derived-flags.md) for the general pattern.

## Related Topics

- [Planned PR Lifecycle](planned-pr-lifecycle.md) - PR body format through lifecycle stages
- [Plan Lifecycle](lifecycle.md) - Overall plan lifecycle
- [Plan Backend Migration](../architecture/plan-backend-migration.md) - Migrating to backend abstraction
- [Derived Flags Pattern](../architecture/derived-flags.md) - effective_force pattern details
