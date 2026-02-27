# Fix Graphite Tracking Divergence at Root Cause

## Context

When running `gt submit` or other `gt` commands, Graphite displays divergence warnings:

```
WARNING: The following branches have diverged from Graphite's tracking:
WARNING: ▸ plnd/remove-ensure-duplication-02-26-1013
```

These appear when a branch's git commit SHA differs from Graphite's cached `branchRevision`. The divergence is introduced when SHA-changing operations (amend, squash, force-update) succeed but the subsequent `retrack_branch` call is never reached due to an intervening failure.

## Root Causes

### Root Cause 1: `rewrite_cmd.py` — Retrack 46 lines after amend

In `_execute_pr_rewrite()`:
- **Line 146**: `amend_commit(cwd, commit_message)` — SHA changes from A to B
- **Line 153-155**: `submit_branch()` — push to remote — **can fail → ClickException exits function**
- **Line 168-173**: `update_pr_title_and_body()` — GitHub API call — **can fail → RuntimeError exits function**
- **Line 192**: `retrack_branch()` — **only reached if ALL preceding operations succeed**

If the push fails or GitHub API fails, the branch is left with a new SHA that Graphite doesn't know about. Every subsequent `gt` command will warn about this divergence.

### Root Cause 2: `checkout_cmd.py` — Force-update without immediate retrack

In `_checkout_pr()`:
- **Line 253**: `_fetch_and_update_branch()` — force-updates local branch to match remote (SHA changes if branch was previously tracked)
- **Line 256-258**: `ensure_branch_has_worktree()` — slot allocation — **can fail**
- **Line 274**: `rebase_onto()` — for stacked PRs — **can fail**
- **Lines 283-296**: Graphite tracking — **only reached if all preceding operations succeed**

If worktree creation or rebase fails, the branch's SHA was already force-updated but never retracked.

### Comparison: `submit_pipeline.py` does it right

In `finalize_pr()`:
- **Line 740**: `amend_commit()` — SHA changes
- **Line 744**: `retrack_branch()` — IMMEDIATELY after amend, no intervening failure points

This is the correct pattern.

## Fix

### Step 1: Move retrack immediately after amend in `rewrite_cmd.py`

**File:** `src/erk/cli/commands/pr/rewrite_cmd.py`

Move the `retrack_branch` call from line 191-192 to immediately after the amend at line 146-147:

```python
# Phase 5: Amend local commit
click.echo(click.style("Phase 4: Amending commit", bold=True))
commit_message = f"{title}\n\n{body}" if body else title
ctx.git.commit.amend_commit(cwd, commit_message)

# Retrack immediately after amend — before push or any failing operation
if ctx.graphite_branch_ops is not None:
    ctx.graphite_branch_ops.retrack_branch(discovery.repo_root, discovery.current_branch)

click.echo(click.style("   Commit amended", fg="green"))
click.echo("")
```

Remove the old retrack at lines 190-192.

This ensures the Graphite cache is updated even if the subsequent push or PR update fails. The push (`gt submit`) will see the correct SHA and push it; the retrack just ensures Graphite's cache matches the local branch pointer.

### Step 2: Add early retrack after force-update in `checkout_cmd.py`

**File:** `src/erk/cli/commands/pr/checkout_cmd.py`

After `_fetch_and_update_branch()` at line 253, add a retrack for branches already tracked by Graphite:

```python
# Fetch and update local branch to match remote
_fetch_and_update_branch(ctx, repo, branch_name=branch_name, pr_number=pr_number)

# Fix Graphite divergence from force-update (if branch was already tracked)
if ctx.branch_manager.is_graphite_managed():
    parent = ctx.branch_manager.get_parent_branch(repo.root, branch_name)
    if parent is not None:
        # Branch was already tracked — force-update changed SHA, retrack now
        ctx.graphite_branch_ops.retrack_branch(repo.root, branch_name)
```

Then simplify the tracking logic at lines 283-296 to only handle the "untracked" case (parent is None → track), since divergence for already-tracked branches is now handled above.

## Key Files

- `src/erk/cli/commands/pr/rewrite_cmd.py` — Move retrack immediately after amend (lines 146→148, remove 190-192)
- `src/erk/cli/commands/pr/checkout_cmd.py` — Add early retrack after `_fetch_and_update_branch` (after line 253)

## Verification

1. Run `make fast-ci` to confirm tests pass
2. Test rewrite failure path: amend succeeds, push fails → verify branch is not diverged (retrack already ran)
3. Test checkout with previously-tracked branch → verify no divergence warning on subsequent `gt` commands
