# Plan: Fix erk crash when run outside git repository

## Problem

`erk` crashes with `RuntimeError: Failed to get repository root` when run outside a git repository because:

1. `main()` in `cli.py:204` calls `log_command_start()`
2. `log_command_start()` calls `_get_current_branch(cwd)`
3. `_get_current_branch()` calls `git.get_repository_root(cwd)` which throws `RuntimeError` when not in a git repo

## Solution

Add `is_in_git_repository(cwd: Path) -> bool` method to Git ABC and use LBYL pattern in `_get_current_branch()`.

## Files to Modify

### 1. Git ABC + 4 Implementations (Gateway pattern)

Per [gateway-abc-implementation.md](docs/learned/architecture/gateway-abc-implementation.md), must implement in 5 places:

**`packages/erk-shared/src/erk_shared/git/abc.py`**
```python
@abstractmethod
def is_in_git_repository(self, cwd: Path) -> bool:
    """Check if the given path is inside a git repository."""
    ...
```

**`packages/erk-shared/src/erk_shared/git/real.py`**
```python
def is_in_git_repository(self, cwd: Path) -> bool:
    """Check if the given path is inside a git repository."""
    if not cwd.exists():
        return False
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
```

**`packages/erk-shared/src/erk_shared/git/fake.py`**
```python
# Add constructor param: in_git_repository: bool = True
def is_in_git_repository(self, cwd: Path) -> bool:
    return self._in_git_repository
```

**`packages/erk-shared/src/erk_shared/git/dry_run.py`**
```python
def is_in_git_repository(self, cwd: Path) -> bool:
    return self._wrapped.is_in_git_repository(cwd)  # Read-only: delegate
```

**`packages/erk-shared/src/erk_shared/git/printing.py`**
```python
def is_in_git_repository(self, cwd: Path) -> bool:
    return self._wrapped.is_in_git_repository(cwd)  # Read-only: delegate silently
```

### 2. Business Logic Fix

**`/Users/schrockn/code/erk/src/erk/core/command_log.py` (lines 55-61)**

```python
# Before:
def _get_current_branch(cwd: Path) -> str | None:
    """Get current git branch if in a git repository."""
    git = RealGit()
    repo_root = git.get_repository_root(cwd)
    if repo_root is None:
        return None
    return git.get_current_branch(repo_root)

# After (LBYL pattern):
def _get_current_branch(cwd: Path) -> str | None:
    """Get current git branch if in a git repository."""
    git = RealGit()
    if not git.is_in_git_repository(cwd):
        return None
    repo_root = git.get_repository_root(cwd)
    return git.get_current_branch(repo_root)
```

### 3. Tests

**`tests/unit/core/test_command_log.py`** - Add test for non-git scenario:
```python
def test_get_current_branch_returns_none_outside_git_repo(tmp_path: Path) -> None:
    """Test _get_current_branch returns None when not in a git repository."""
    from erk.core.command_log import _get_current_branch
    result = _get_current_branch(tmp_path)
    assert result is None
```

**`tests/integration/test_real_git.py`** - Add integration test for `is_in_git_repository()`:
```python
def test_is_in_git_repository_returns_true_in_repo(tmp_path: Path) -> None:
    """Test is_in_git_repository returns True inside a git repo."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    git = RealGit()
    assert git.is_in_git_repository(tmp_path) is True

def test_is_in_git_repository_returns_false_outside_repo(tmp_path: Path) -> None:
    """Test is_in_git_repository returns False outside a git repo."""
    git = RealGit()
    assert git.is_in_git_repository(tmp_path) is False
```

## Related Documentation

- `dignified-python` skill - LBYL pattern
- `fake-driven-testing` skill - test patterns
- [gateway-abc-implementation.md](docs/learned/architecture/gateway-abc-implementation.md) - 5-file checklist