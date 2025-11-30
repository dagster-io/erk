# Plan: Add "Last Commit Time" Column to `erk wt ls`

## Goal

Add an optional `--last-commit` flag to `erk wt ls` that displays a "last" column showing the author date of each branch's tip commit as relative time (e.g., "2d ago").

## Approach

Use `git for-each-ref` to batch-fetch author dates for all branches in a single subprocess call. This is fast (~single git call) and author dates are preserved through rebases, so it shows when work was actually written.

## Implementation

### Step 1: Add Batch Method to Git ABC

**File:** `/Users/schrockn/code/erk/packages/erk-shared/src/erk_shared/git/abc.py`

```python
@abstractmethod
def get_all_branch_author_dates(self, repo_root: Path) -> dict[str, str]:
    """Get the author date of the HEAD commit for all local branches.

    Returns dict mapping branch name to ISO 8601 timestamp.
    Author dates are preserved through rebases.
    """
    ...
```

### Step 2: Implement in RealGit

**File:** `/Users/schrockn/code/erk/packages/erk-shared/src/erk_shared/git/real.py`

```python
def get_all_branch_author_dates(self, repo_root: Path) -> dict[str, str]:
    result = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)\t%(authordate:iso-strict)", "refs/heads/"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}

    dates: dict[str, str] = {}
    for line in result.stdout.strip().split("\n"):
        if "\t" in line:
            branch, date = line.split("\t", 1)
            dates[branch] = date
    return dates
```

### Step 3: Implement in FakeGit

**File:** `/Users/schrockn/code/erk/src/erk/core/git/fake.py`

- Add `branch_author_dates: dict[str, str] | None = None` constructor parameter
- Store as `self._branch_author_dates`
- Implement method returning `self._branch_author_dates or {}`

### Step 4: Update list_cmd.py

**File:** `/Users/schrockn/code/erk/src/erk/cli/commands/wt/list_cmd.py`

Add `--last-commit` flag to command:

```python
@click.option("--last-commit", is_flag=True, help="Show last commit time column")
```

Add helper function:

```python
def _format_last_commit_cell(timestamp: str | None) -> str:
    if timestamp is None:
        return "-"
    return format_relative_time(timestamp) or "-"
```

Update `_list_worktrees()`:

- Accept `show_last_commit: bool` parameter
- If True, fetch dates once: `author_dates = ctx.git.get_all_branch_author_dates(repo.root)`
- Add column conditionally: `if show_last_commit: table.add_column("last", no_wrap=True)`
- For each row, look up `author_dates.get(branch)` and format

### Step 5: Tests

**Unit tests** in `/Users/schrockn/code/erk/tests/unit/commands/wt/test_list_helpers.py`:

- Test `_format_last_commit_cell` with valid timestamp
- Test `_format_last_commit_cell` with None returns "-"

**Command tests**:

- Test `erk wt ls` (default) does NOT show "last" column
- Test `erk wt ls --last-commit` shows "last" column with timestamps

## Edge Cases

- **Detached HEAD**: Returns "-" (branch not in author_dates dict)
- **Trunk branch**: Shows its author date (no special handling needed)
- **Flag not provided**: Column not shown, no git call made

## Performance

- Single `git for-each-ref` call for all branches
- Only called when `--last-commit` flag is provided
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
