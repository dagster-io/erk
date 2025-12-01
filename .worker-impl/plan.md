# Plan: Merge GitHubGtKit into GitHub(ABC)

## Goal

Consolidate all GitHub operations under a single `GitHub(ABC)` interface by:
1. Adding GitHubGtKit methods to GitHub(ABC) with explicit parameters
2. Removing GitHubGtKit entirely
3. Updating all callers to use the unified interface

## Summary of Changes

- **Add 8 new methods** to `GitHub(ABC)`
- **Modify 1 method** (`merge_pr` - expanded signature)
- **Remove** `GitHubGtKit(ABC)`, `RealGitHubGtKit`, `FakeGitHubGtKitOps`
- **Update** `GtKit.github()` to return `GitHub` instead of `GitHubGtKit`
- **Extend** `FakeGitHub` with GT-kit state and methods

## Implementation Steps

### Step 1: Add New Methods to GitHub(ABC)

File: `packages/erk-shared/src/erk_shared/github/abc.py`

Add these abstract methods (all with explicit `repo_root: Path` parameter):

```python
@abstractmethod
def get_pr_info_for_branch(self, repo_root: Path, branch: str) -> tuple[int, str] | None:
    """Get PR number and URL for a branch. Returns (number, url) or None."""

@abstractmethod
def get_pr_state_for_branch(self, repo_root: Path, branch: str) -> tuple[int, str] | None:
    """Get PR number and state for a branch. Returns (number, state) or None."""

@abstractmethod
def get_pr_title(self, repo_root: Path, pr_number: int) -> str | None:
    """Get the title of a specific PR."""

@abstractmethod
def get_pr_body(self, repo_root: Path, pr_number: int) -> str | None:
    """Get the body of a specific PR."""

@abstractmethod
def get_pr_diff(self, repo_root: Path, pr_number: int) -> str:
    """Get the diff for a PR."""

@abstractmethod
def update_pr_metadata(self, repo_root: Path, pr_number: int, title: str, body: str) -> bool:
    """Update PR title and body. Returns True on success."""

@abstractmethod
def mark_pr_ready(self, repo_root: Path, pr_number: int) -> bool:
    """Mark a draft PR as ready for review. Returns True on success."""

@abstractmethod
def get_graphite_pr_url(self, repo_root: Path, pr_number: int) -> str | None:
    """Get Graphite PR URL for a PR."""
```

Modify existing `merge_pr` to add optional commit message parameters:

```python
@abstractmethod
def merge_pr(
    self,
    repo_root: Path,
    pr_number: int,
    *,
    squash: bool = True,
    subject: str | None = None,  # NEW
    body: str | None = None,      # NEW
    verbose: bool = False,
) -> bool:  # CHANGED from None to bool
```

### Step 2: Implement New Methods in RealGitHub

File: `src/erk/core/github/real.py`

Implement all 8 new methods using `gh` CLI subprocess calls. Port the implementation logic from `RealGitHubGtKit` in `packages/erk-shared/src/erk_shared/integrations/gt/real.py`.

### Step 3: Extend FakeGitHub with Builder Pattern

File: `src/erk/core/github/fake.py`

Add new constructor parameters and implement new methods:

```python
def __init__(
    self,
    *,
    # ... existing params ...
    # NEW: GT-kit state
    pr_titles: dict[int, str] | None = None,
    pr_bodies: dict[int, str] | None = None,
    pr_diffs: dict[int, str] | None = None,
    merge_should_fail: bool = False,
    pr_has_conflicts: bool = False,
):
```

Add mutation tracking:
```python
self._updated_metadata: list[tuple[int, str, str]] = []  # (pr_number, title, body)
self._marked_ready: list[int] = []
```

**Add declarative builder methods** (migrated from FakeGtKitOps):
```python
def with_pr(self, branch: str, number: int, url: str, ...) -> "FakeGitHub":
    """Declarative PR setup for testing."""
    self._prs[branch] = PullRequestInfo(...)
    return self

def with_merge_failure(self) -> "FakeGitHub":
    """Configure merge to fail."""
    self._merge_should_fail = True
    return self

def with_pr_conflicts(self) -> "FakeGitHub":
    """Configure PR to have merge conflicts."""
    self._pr_has_conflicts = True
    return self
```

### Step 4: Update DryRunGitHub and Stub RealGitHub

Files:
- `src/erk/core/github/dry_run.py`
- `packages/erk-shared/src/erk_shared/github/real.py`

Add implementations for all 8 new methods (dry-run versions that log but don't execute).

### Step 5: Update GtKit Composite

File: `packages/erk-shared/src/erk_shared/integrations/gt/abc.py`

Change `GtKit.github()` return type:

```python
class GtKit(ABC):
    @abstractmethod
    def github(self) -> GitHub:  # Changed from GitHubGtKit
        """Get the GitHub operations interface."""
```

### Step 6: Update RealGtKitOps

File: `packages/erk-shared/src/erk_shared/integrations/gt/real.py`

- Change `github()` to return a `RealGitHub` instance
- Remove `RealGitHubGtKit` class entirely

### Step 7: Update FakeGtKitOps

File: `packages/erk-shared/src/erk_shared/integrations/gt/fake.py`

- Change `github()` to return a `FakeGitHub` instance
- Update `.with_pr()`, `.with_merge_failure()`, etc. to configure `FakeGitHub`
- Remove `FakeGitHubGtKitOps` class and `GitHubState` dataclass

### Step 8: Migrate GT Kit CLI Commands

Files:
- `packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/submit_branch.py`
- `packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/land_pr.py`
- `packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/pr_update.py`

Update to use explicit parameters:

```python
# Before (implicit current branch):
pr_info = ops.github().get_pr_info()

# After (explicit parameters):
branch = ops.git().get_current_branch()
repo_root = Path(ops.git().get_repository_root())
pr_info = ops.github().get_pr_info_for_branch(repo_root, branch)
```

### Step 9: Delete Duplicate fake_ops.py

File: `packages/dot-agent-kit/tests/unit/kits/gt/fake_ops.py`

Delete this file and update imports to use `erk_shared.integrations.gt.fake`.

### Step 10: Remove GitHubGtKit

File: `packages/erk-shared/src/erk_shared/integrations/gt/abc.py`

Delete `GitHubGtKit` class entirely.

### Step 11: Update Exports

File: `packages/erk-shared/src/erk_shared/integrations/gt/__init__.py`

Remove `GitHubGtKit`, `RealGitHubGtKit` from exports.

### Step 12: Update Tests

Files to update:
- `packages/dot-agent-kit/tests/unit/kits/gt/test_submit_branch.py`
- `packages/dot-agent-kit/tests/unit/kits/gt/test_land_pr.py`
- `packages/dot-agent-kit/tests/unit/kits/gt/test_pr_update.py`
- `packages/dot-agent-kit/tests/unit/kits/gt/test_real_ops.py`

Update test assertions and fake setup to use new patterns.

## Critical Files Summary

| File | Action |
|------|--------|
| `packages/erk-shared/src/erk_shared/github/abc.py` | Add 8 methods, modify merge_pr |
| `src/erk/core/github/real.py` | Implement 8 new methods |
| `src/erk/core/github/fake.py` | Extend with GT-kit state |
| `packages/erk-shared/src/erk_shared/integrations/gt/abc.py` | Update GtKit, delete GitHubGtKit |
| `packages/erk-shared/src/erk_shared/integrations/gt/real.py` | Update, delete RealGitHubGtKit |
| `packages/erk-shared/src/erk_shared/integrations/gt/fake.py` | Update, delete FakeGitHubGtKitOps |
| GT kit CLI commands (3 files) | Migrate to explicit parameters |
| GT kit tests (4 files) | Update for new interface |

## Risk Mitigation

1. **Incremental approach**: Add new methods first (non-breaking), then migrate callers, then delete old code
2. **Test coverage**: Run full test suite after each step to catch regressions
3. **Return type change for merge_pr**: From `None` to `bool` - callers that ignore return value unaffected