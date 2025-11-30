# Plan: Add "Last Commit Time" Column to `erk wt ls`

## Goal
Add an optional `--last-commit` flag to `erk wt ls` that displays a "last" column showing the author date of the most recent commit **unique to each branch** (not from trunk), displayed as relative time (e.g., "2d ago").

## Approach
Use `git log trunk..branch -1 --format=%aI` per branch to get the author date of the last commit that exists on the branch but not on trunk. This is slower than batch approaches (~0.1s per branch) but semantically correct - it only shows commits you actually wrote on that branch.

## Implementation

### Step 1: Add Method to Git ABC
**File:** `/Users/schrockn/code/erk/packages/erk-shared/src/erk_shared/git/abc.py`

```python
@abstractmethod
def get_branch_last_commit_time(self, repo_root: Path, branch: str, trunk: str) -> str | None:
    """Get the author date of the most recent commit unique to a branch.

    Returns ISO 8601 timestamp of the latest commit on `branch` but not on `trunk`,
    or None if branch has no unique commits or doesn't exist.
    """
    ...
```

### Step 2: Implement in RealGit
**File:** `/Users/schrockn/code/erk/packages/erk-shared/src/erk_shared/git/real.py`

```python
def get_branch_last_commit_time(self, repo_root: Path, branch: str, trunk: str) -> str | None:
    result = subprocess.run(
        ["git", "log", f"{trunk}..{branch}", "-1", "--format=%aI"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    timestamp = result.stdout.strip()
    return timestamp if timestamp else None
```

### Step 3: Implement in FakeGit
**File:** `/Users/schrockn/code/erk/src/erk/core/git/fake.py`

- Add `branch_last_commit_times: dict[str, str] | None = None` constructor parameter
- Store as `self._branch_last_commit_times`
- Implement method returning `self._branch_last_commit_times.get(branch)`

### Step 4: Update list_cmd.py
**File:** `/Users/schrockn/code/erk/src/erk/cli/commands/wt/list_cmd.py`

Add `--last-commit` flag to command:
```python
@click.option("--last-commit", is_flag=True, help="Show last commit time column")
```

Add helper function:
```python
def _format_last_commit_cell(
    ctx: ErkContext, repo_root: Path, branch: str | None, trunk: str
) -> str:
    if branch is None or branch == trunk:
        return "-"
    timestamp = ctx.git.get_branch_last_commit_time(repo_root, branch, trunk)
    if timestamp is None:
        return "-"
    return format_relative_time(timestamp) or "-"
```

Update `_list_worktrees()`:
- Accept `show_last_commit: bool` parameter
- Get trunk once: `trunk = ctx.git.get_trunk_branch(repo.root)`
- Add column conditionally: `if show_last_commit: table.add_column("last", no_wrap=True)`
- For each worktree row, call `_format_last_commit_cell(ctx, repo.root, branch, trunk)`

### Step 5: Tests

**Unit tests** in `/Users/schrockn/code/erk/tests/unit/commands/wt/test_list_helpers.py`:
- Test `_format_last_commit_cell` with valid timestamp returns relative time
- Test with None branch (detached HEAD) returns "-"
- Test with trunk branch returns "-"
- Test with no unique commits returns "-"

**Command tests**:
- Test `erk wt ls` (default) does NOT show "last" column
- Test `erk wt ls --last-commit` shows "last" column with timestamps

## Edge Cases
- **Detached HEAD**: Returns "-" (branch is None)
- **No unique commits**: Returns "-" (git returns empty - branch is at same commit as trunk)
- **Trunk branch**: Returns "-" (explicitly skipped)
- **Branch doesn't exist**: Returns "-" (git fails gracefully)

## Performance
- Per-branch `git log` calls: ~0.1s per branch
- For 15 worktrees: ~1.5s overhead
- Only incurred when `--last-commit` flag is provided
- No performance impact on default `erk wt ls`

## Column Order (with --last-commit)
```
worktree | branch | pr | sync | last | impl
```

## Critical Files
1. `/Users/schrockn/code/erk/packages/erk-shared/src/erk_shared/git/abc.py`
2. `/Users/schrockn/code/erk/packages/erk-shared/src/erk_shared/git/real.py`
3. `/Users/schrockn/code/erk/src/erk/core/git/fake.py`
4. `/Users/schrockn/code/erk/src/erk/cli/commands/wt/list_cmd.py`
5. `/Users/schrockn/code/erk/tests/unit/commands/wt/test_list_helpers.py`