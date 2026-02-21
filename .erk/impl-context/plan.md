# Fix: Non-fast-forward push in draft-PR plan submission

## Context

When submitting a draft-PR plan for implementation via `erk plan submit` (or TUI), the `_submit_draft_pr_plan()` function in `submit.py` checks out the existing plan branch, creates `.worker-impl/`, commits, and pushes. However, it skips the `pull_rebase()` step that syncs the local branch with remote. If the remote branch has diverged (e.g., from a prior submission attempt or CI), the push fails with a non-fast-forward error.

The documented three-step sync pattern from `docs/learned/planning/draft-pr-branch-sync.md` is:
```
fetch_branch → checkout/create_tracking → pull_rebase
```

But `_submit_draft_pr_plan()` only does:
```
fetch_branch → checkout/create_tracking → (missing pull_rebase) → commit → push
```

## Fix

**File**: `src/erk/cli/commands/submit.py`

1. Add `PullRebaseError` to the imports from `erk_shared.gateway.git.remote_ops.types`
2. After the branch checkout (line 438) and before `.worker-impl/` cleanup (line 441), add a `pull_rebase()` call to sync with remote

The pull_rebase is needed when:
- The branch already existed locally (may be behind remote)
- The branch was just created as a tracking branch (already at remote HEAD, but pull_rebase is a no-op in this case)

So we can unconditionally call it after checkout.

## Verification

- Run the unit tests for submit
- Manually test by submitting a draft-PR plan where the local branch is behind remote
