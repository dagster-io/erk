# Plan: Modify erk wt ls to Show Last Commit Info by Default

## Summary

Modify `erk wt ls` command to:

1. Remove `--last-commit` flag and make commit info the default behavior
2. Rename "last" column to "last cmt"
3. Add "cmt" column showing git short hash of the last unique commit

## Implementation Steps

### Step 1: Add `get_branch_last_commit_sha` to Git ABC

**File:** `packages/erk-shared/src/erk_shared/git/abc.py`

Add new abstract method after `get_branch_last_commit_time`:

```python
@abstractmethod
def get_branch_last_commit_sha(self, repo_root: Path, branch: str, trunk: str) -> str | None:
    """Get the short SHA of the most recent commit unique to a branch.

    Returns 7-character short SHA of the latest commit on `branch` but not on `trunk`,
    or None if branch has no unique commits or doesn't exist.
    """
    ...
```

### Step 2: Implement in RealGit

**File:** `packages/erk-shared/src/erk_shared/git/real.py`

Add implementation after `get_branch_last_commit_time`:

```python
def get_branch_last_commit_sha(self, repo_root: Path, branch: str, trunk: str) -> str | None:
    """Get the short SHA of the most recent commit unique to a branch."""
    result = subprocess.run(
        ["git", "log", f"{trunk}..{branch}", "-1", "--format=%h"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha if sha else None
```

### Step 3: Implement in FakeGit

**File:** `src/erk/core/git/fake.py`

Add constructor parameter and implementation:

- Add `branch_last_commit_shas: dict[str, str] | None = None` to constructor
- Implement method to return from the dict

### Step 4: Implement in DryRunGit

**File:** `src/erk/core/git/dry_run.py`

Delegate to wrapped implementation (read-only operation):

```python
def get_branch_last_commit_sha(self, repo_root: Path, branch: str, trunk: str) -> str | None:
    return self._git.get_branch_last_commit_sha(repo_root, branch, trunk)
```

### Step 5: Modify list_cmd.py

**File:** `src/erk/cli/commands/wt/list_cmd.py`

#### 5a. Add `_format_commit_sha_cell` function

After `_format_last_commit_cell`:

```python
def _format_commit_sha_cell(
    ctx: ErkContext, repo_root: Path, branch: str | None, trunk: str
) -> str:
    """Format commit SHA cell for Rich table."""
    if branch is None or branch == trunk:
        return "-"
    sha = ctx.git.get_branch_last_commit_sha(repo_root, branch, trunk)
    return sha if sha else "-"
```

#### 5b. Update `_list_worktrees` function

- Remove `show_last_commit` parameter (always show)
- Always get trunk branch at line 225
- Rename column "last" → "last cmt"
- Add column "cmt" after "last cmt" (order: sync, last cmt, cmt, impl)
- Remove conditional logic for `show_last_commit`
- Update table row building for both root and non-root worktrees to always include both columns

#### 5c. Update `list_wt` command

- Remove `@click.option("--last-commit", ...)` decorator
- Remove `last_commit: bool` parameter
- Update docstring to remove reference to flag
- Call `_list_worktrees(ctx)` without the flag

### Step 6: Update Unit Tests

**File:** `tests/unit/commands/wt/test_list_helpers.py`

- Add tests for new `_format_commit_sha_cell` function
- Update any tests that reference column order or `show_last_commit`

### Step 7: Update FakeGit Tests (if needed)

**File:** `tests/fakes/git.py` or `tests/unit/fakes/test_fake_git.py`

- Ensure FakeGit implementation is tested

## Files to Modify

1. `packages/erk-shared/src/erk_shared/git/abc.py` - Add abstract method
2. `packages/erk-shared/src/erk_shared/git/real.py` - Add implementation
3. `src/erk/core/git/fake.py` - Add fake implementation
4. `src/erk/core/git/dry_run.py` - Add delegation
5. `src/erk/cli/commands/wt/list_cmd.py` - Main changes
6. `tests/unit/commands/wt/test_list_helpers.py` - Update tests

## Expected Output Change

Before (with `--last-commit`):

```
worktree   branch    pr    sync      last      impl
root       (main)    -     current   -         -
feature    (=)       ✅ #1  current   2d ago    #42
```

After (columns: last cmt, cmt, impl):

```
worktree   branch    pr    sync      last cmt   cmt       impl
root       (main)    -     current   -          -         -
feature    (=)       ✅ #1  current   2d ago     abc1234   #42
```
