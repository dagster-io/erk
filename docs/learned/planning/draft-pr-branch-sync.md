---
title: Draft PR Branch Sync
read_when:
  - "implementing or debugging draft-PR plan setup"
  - "understanding branch sync during plan implementation"
  - "working with setup_impl_from_issue for draft PR plans"
  - "debugging divergence between local and remote plan branches"
tripwires:
  - action: "implementing draft-PR plan without syncing with remote"
    warning: "Before implementing a draft-PR plan, always sync with remote: fetch_branch -> checkout/create_tracking -> pull_rebase"
  - action: "detecting plan backend by checking backend type directly"
    warning: "Use plan.header_fields.get(BRANCH_NAME) to detect draft-PR plans. This is backend-agnostic and works across all backends."
  - action: "creating a new branch for a draft-PR plan"
    warning: "Draft-PR plans already have a branch created during plan-save. Reuse the existing branch, don't create a new one."
  - action: "committing to draft-PR plan branches after checkout without pulling remote"
    warning: "Both setup_impl_from_issue.py and submit.py use the same three-step sync: fetch_branch -> checkout/create_tracking -> pull_rebase. Skipping pull_rebase causes non-fast-forward push failures."
---

# Draft PR Branch Sync

When implementing a draft-PR plan, the local branch must be synced with remote because plan-save creates the branch and pushes it, then checks out the original branch. Remote may receive additional commits before implementation runs.

## The Problem

1. `plan_save` creates a branch, pushes it to remote, creates draft PR
2. `plan_save` checks out the original branch (user continues working)
3. Time passes (remote CI may add commits, user may re-plan)
4. `plan-implement` runs and needs the latest branch state

## Three-Step Sync Sequence

In `setup_impl_from_issue.py`, the sync follows this pattern:

```
fetch_branch → checkout/create_tracking → pull_rebase
```

### Step 1: Fetch Branch

<!-- Source: src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py:114 -->

Calls `git.remote.fetch_branch()` to fetch the named branch from origin, making remote state available locally.

### Step 2: Checkout or Create Tracking

Three possible states:

| State                 | Action                                                                                                 |
| --------------------- | ------------------------------------------------------------------------------------------------------ |
| Already on branch     | Skip checkout, proceed to pull                                                                         |
| Branch exists locally | `branch_manager.checkout_branch(cwd, branch_name)`                                                     |
| Branch only on remote | `branch_manager.create_tracking_branch(repo_root, branch_name, f"origin/{branch_name}")` then checkout |

### Step 3: Pull Rebase

<!-- Source: src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py:132 -->

Calls `git.remote.pull_rebase()` to fast-forward the local branch to remote HEAD. Only needed when already on branch or after checking out an existing local branch. Skip when creating a fresh tracking branch (already at remote HEAD).

## Backend Detection

The branch name is stored in the plan's header fields. Detection uses a backend-agnostic pattern:

<!-- Source: src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py:103-112 -->

Reads `plan.header_fields.get(BRANCH_NAME)`. If the result is a non-empty string, this is a draft-PR plan (reuse the existing branch and sync with remote). Otherwise, it is an issue-based plan (generate a new branch name).

## Backend-Aware Branching

The `create_cmd.py` branch creation also handles the two backends explicitly:

<!-- Source: src/erk/cli/commands/branch/create_cmd.py:164-198 -->

For `draft_pr` backend: the branch was created by plan-save and is expected to exist on remote — fetches and creates a tracking branch if needed. For `github` (issue-based) backend: standard path, creates a new branch which must not already exist. Any other backend raises `RuntimeError`.

## Idempotent Design

`setup-impl-from-issue` is safe to run multiple times:

- If already on the correct branch, it syncs with remote
- If branch exists locally, it checks out and syncs
- If branch only exists on remote, it creates tracking and checks out

This is why `plan-implement` always calls `setup-impl-from-issue` even when `.impl/` already exists with issue tracking.

## Pattern Consistency: Setup and Submit

Both `setup_impl_from_issue.py` and `submit.py` use an identical three-step sync pattern when working with draft-PR plan branches:

<!-- Source: src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py:81-97 -->
<!-- Source: src/erk/cli/commands/submit.py:431-445 -->

Both paths call the same three-step sequence: `fetch_branch()` → `create_tracking_branch()` / `checkout_branch()` → `pull_rebase()`. See the source files for exact call signatures.

PR #7697 added the missing `pull_rebase()` call to the submit path. Without it, the submit path would attempt to push commits onto a branch that had diverged from remote, causing non-fast-forward push failures.

## Issue-Based Plan Branching

For comparison, issue-based plans generate fresh branch names:

<!-- Source: src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py:155-157 -->

Calls `generate_issue_branch_name()` with the issue number, plan title, timestamp, and optional objective ID. Branch names follow the pattern `P{issue}-{slugified-title}-{timestamp}`.

If already on a branch matching the expected prefix (`P{issue_number}-`), the existing branch is reused.

## Related Topics

- [Draft PR Lifecycle](draft-pr-lifecycle.md) - PR body format through lifecycle stages
- [Plan Lifecycle](lifecycle.md) - Overall plan lifecycle
- [Plan Backend Migration](../architecture/plan-backend-migration.md) - Migrating to backend abstraction
