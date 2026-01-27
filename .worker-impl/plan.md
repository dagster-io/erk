# Plan: Make delete_branch Idempotent

## Problem

The `erk land` command fails at cleanup when the branch to delete doesn't exist locally:

```
RuntimeError: Failed to delete branch 'P6149-erk-plan-move-codespacere-01-27-0142'
stderr: error: branch 'P6149-erk-plan-move-codespacere-01-27-0142' not found
```

This happens when the branch was already deleted by an earlier cleanup step (e.g., worktree removal).

## Root Cause

`RealGitBranchOps.delete_branch()` in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py:38-45` doesn't check if the branch exists before attempting deletion.

## Solution

Make `delete_branch` idempotent using LBYL (Look Before You Leap) pattern per dignified-python standards:

1. Check if branch exists using `git show-ref --verify refs/heads/{branch_name}`
2. If branch doesn't exist (returncode != 0), return early - the goal is achieved
3. If branch exists, proceed with the delete

## Files to Modify

**`packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py`**

```python
def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
    """Delete a local branch.

    Idempotent: if branch doesn't exist, returns successfully.
    """
    # LBYL: Check if branch exists before attempting delete
    check_result = subprocess.run(
        ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
        cwd=cwd,
        capture_output=True,
        check=False,
    )
    if check_result.returncode != 0:
        # Branch doesn't exist - goal achieved
        return

    flag = "-D" if force else "-d"
    run_subprocess_with_context(
        cmd=["git", "branch", flag, branch_name],
        operation_context=f"delete branch '{branch_name}'",
        cwd=cwd,
    )
```

**`packages/erk-shared/src/erk_shared/gateway/git/branch_ops/fake.py`**

Update fake to match real behavior - check `local_branches` before tracking delete:

```python
def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
    # Check if we should raise an exception for this branch
    if branch_name in self._delete_branch_raises:
        exc = self._delete_branch_raises[branch_name]
        if isinstance(exc, subprocess.CalledProcessError):
            raise RuntimeError(f"Failed to delete branch {branch_name}") from exc
        raise exc

    # Idempotent: track delete even if branch doesn't exist (matches real behavior)
    self._deleted_branches.append(branch_name)
```

(No change needed - fake already doesn't error on missing branches)

## Test Plan

Add test for idempotent delete behavior:

**`tests/unit/gateway/git/branch_ops/test_real_git_branch_ops.py`** (new file or add to existing)

```python
def test_delete_branch_idempotent_when_branch_missing(tmp_path: Path) -> None:
    """delete_branch succeeds when branch doesn't exist."""
    # Create a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp_path, check=True)

    ops = RealGitBranchOps()
    # Should not raise - branch "nonexistent" doesn't exist
    ops.delete_branch(tmp_path, "nonexistent", force=False)
```

## Verification

1. Run unit tests for branch_ops: `pytest tests/unit/gateway/git/branch_ops/ -v`
2. Run the failing scenario manually: attempt to delete a non-existent branch
3. Run full CI: `make fast-ci`