# Plan: Auto-fix Graphite Tracking Divergence

## Problem

When `gt restack` rebases a branch, it creates new commit SHAs. Graphite's internal tracking (`.graphite_cache_persist`) still points to old SHAs, leaving the branch "diverged" from Graphite's perspective. This causes `gt track` on child branches to fail with "Cannot perform this operation on diverged branch."

## Solution

Two fixes providing defense-in-depth:

1. **Fix in `erk pr sync`**: After restack, auto-fix divergence
2. **Fix in `GraphiteBranchManager.create_branch()`**: Before tracking child, auto-fix diverged parent

## Files to Modify

### 1. Add `retrack_branch()` to GraphiteBranchOps (5 files)

New abstract method to re-track an existing branch (refresh Graphite's SHA tracking):

**`packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/abc.py`**
```python
@abstractmethod
def retrack_branch(self, cwd: Path, branch_name: str) -> None:
    """Re-track an existing branch to fix divergence.

    Runs `gt track` on the current branch to update Graphite's internal
    SHA tracking after rebase/restack operations.
    """
    ...
```

**Implement in all 5 locations per gateway-abc-implementation tripwire:**
- `abc.py` - abstract method
- `real.py` - `subprocess.run(["gt", "track"], cwd=cwd)`
- `fake.py` - update fake state
- `dry_run.py` - delegate to real
- `printing.py` - print and delegate

### 2. Add `is_branch_diverged_from_tracking()` to Graphite ABC (5 files)

New method to detect Graphite-internal divergence:

**`packages/erk-shared/src/erk_shared/gateway/graphite/abc.py`**
```python
@abstractmethod
def is_branch_diverged_from_tracking(self, git: Git, repo_root: Path, branch: str) -> bool:
    """Check if branch is diverged from Graphite's tracked SHA.

    Compares Graphite's cached branchRevision with actual git HEAD.
    Returns True if they differ (branch needs re-tracking).
    """
    ...
```

**Implement in all 5 gateway files.**

### 3. Update `sync_cmd.py` - Fix 1

**File:** `src/erk/cli/commands/pr/sync_cmd.py`

Add auto-fix after restack operations at **two locations**:

**After line 240** (already-tracked branch path):
```python
user_output(click.style("✓", fg="green") + " Branch restacked")

# Auto-fix Graphite tracking divergence after restack
if ctx.graphite.is_branch_diverged_from_tracking(ctx.git, repo.root, current_branch):
    user_output("Fixing Graphite tracking divergence...")
    ctx.graphite_branch_ops.retrack_branch(repo.root, current_branch)
    user_output(click.style("✓", fg="green") + " Graphite tracking updated")

return
```

**After line 296** (new branch path):
```python
user_output(click.style("✓", fg="green") + " Branch restacked")

# Auto-fix Graphite tracking divergence after restack
if ctx.graphite.is_branch_diverged_from_tracking(ctx.git, repo.root, current_branch):
    user_output("Fixing Graphite tracking divergence...")
    ctx.graphite_branch_ops.retrack_branch(repo.root, current_branch)
    user_output(click.style("✓", fg="green") + " Graphite tracking updated")

# Step 8: Submit to link with Graphite
```

### 4. Update `GraphiteBranchManager.create_branch()` - Fix 2

**File:** `packages/erk-shared/src/erk_shared/branch_manager/graphite.py`

Add parent divergence check **before line 103** (before tracking child):

```python
# Auto-fix diverged parent before tracking child
# (gt track fails if parent is diverged from Graphite's tracking)
if self.graphite.is_branch_diverged_from_tracking(self.git, repo_root, parent_for_graphite):
    # Save current branch, checkout parent, retrack, restore
    self.git_branch_ops.checkout_branch(repo_root, parent_for_graphite)
    self.graphite_branch_ops.retrack_branch(repo_root, parent_for_graphite)
    self.git_branch_ops.checkout_branch(repo_root, branch_name)

self.graphite_branch_ops.track_branch(repo_root, branch_name, parent_for_graphite)
```

## Implementation Notes

### Detecting Divergence (real.py)

```python
def is_branch_diverged_from_tracking(self, git: Git, repo_root: Path, branch: str) -> bool:
    branches = self.get_all_branches(git, repo_root)
    if branch not in branches:
        return False  # Not tracked = not diverged

    tracked_sha = branches[branch].commit_sha
    actual_sha = git.get_branch_head(repo_root, branch)
    return tracked_sha != actual_sha
```

**Note:** The `get_all_branches()` parsing already gets the actual git SHA. Need to also extract `branchRevision` from `.graphite_cache_persist` to compare.

### Re-tracking (real.py)

```python
def retrack_branch(self, cwd: Path, branch_name: str) -> None:
    # gt track with no args re-tracks the current branch
    run_subprocess_with_context(
        cmd=["gt", "track"],
        operation_context=f"re-track branch '{branch_name}'",
        cwd=cwd,
    )
```

## Verification

1. **Reproduce the issue:**
   ```bash
   erk pr sync --dangerous  # Leaves branch diverged
   erk plan submit <issue>  # Should now work (Fix 1 prevents divergence)
   ```

2. **Test Fix 2 (defense-in-depth):**
   ```bash
   # Manually cause divergence
   gt restack
   # Don't run gt track
   erk plan submit <issue>  # Should auto-fix parent and succeed
   ```

3. **Run tests:**
   ```bash
   make fast-ci
   ```

4. **Add unit tests:**
   - Test `is_branch_diverged_from_tracking()` with FakeGraphite
   - Test `retrack_branch()` with FakeGraphite
   - Test sync_cmd auto-fixes divergence after restack
   - Test create_branch auto-fixes diverged parent