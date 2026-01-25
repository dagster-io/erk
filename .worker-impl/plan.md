# Phase 2A: Branch Subgateway Steelthread

Part of Objective #5292 (Git Gateway Facade Refactoring), Step 2A

## Goal

Wire the existing `GitBranchOps` subgateway into the Git ABC as a `branch` property, following the pattern established by the Worktree subgateway in Phase 1.

## Current State

**GitBranchOps already exists** at `packages/erk-shared/src/erk_shared/git/branch_ops/`:
- `abc.py` - GitBranchOps ABC with 5 methods
- `real.py` - RealGitBranchOps
- `fake.py` - FakeGitBranchOps
- `dry_run.py` - DryRunGitBranchOps
- `printing.py` - PrintingGitBranchOps

**But it's NOT wired into Git ABC**:
- Currently: `git_branch_ops` is a separate field on ErkContext
- BranchManager receives it as a constructor parameter
- Target: `ctx.git.branch.checkout_branch()` (like `ctx.git.worktree.list_worktrees()`)

## Implementation Steps

### Step 1: Add `branch` Property to Git ABC

**File: `packages/erk-shared/src/erk_shared/git/abc.py`**

```python
# Add to TYPE_CHECKING imports
if TYPE_CHECKING:
    from erk_shared.git.worktree.abc import Worktree
    from erk_shared.git.branch_ops.abc import GitBranchOps  # ADD THIS

# Add abstract property (after worktree property, ~line 102)
@property
@abstractmethod
def branch(self) -> GitBranchOps:
    """Access branch operations subgateway."""
    ...
```

### Step 2: Implement in RealGit

**File: `packages/erk-shared/src/erk_shared/git/real.py`**

```python
# Add import
from erk_shared.git.branch_ops.abc import GitBranchOps
from erk_shared.git.branch_ops.real import RealGitBranchOps

# In __init__, add (after self._worktree):
self._branch = RealGitBranchOps(time=self._time)

# Add property (after worktree property)
@property
def branch(self) -> GitBranchOps:
    """Access branch operations subgateway."""
    return self._branch
```

### Step 3: Implement in FakeGit

**File: `packages/erk-shared/src/erk_shared/git/fake.py`**

```python
# Import already exists, just need to add the property

# In __init__, instantiate (around line 263, after worktree gateway):
self._branch_gateway = FakeGitBranchOps(
    worktrees=self._worktrees,
    current_branches=self._current_branches,
    local_branches=self._local_branches,
    delete_branch_raises=self._delete_branch_raises,
    tracking_branch_failures=self._tracking_branch_failures,
)

# Add property (after worktree property)
@property
def branch(self) -> GitBranchOps:
    """Access branch operations subgateway."""
    return self._branch_gateway

# Update create_linked_branch_ops() to return self._branch_gateway
# instead of creating a new instance
```

### Step 4: Implement in DryRunGit

**File: `packages/erk-shared/src/erk_shared/git/dry_run.py`**

```python
# Add imports
from erk_shared.git.branch_ops.abc import GitBranchOps
from erk_shared.git.branch_ops.dry_run import DryRunGitBranchOps

# Add property (after worktree property, ~line 48)
@property
def branch(self) -> GitBranchOps:
    """Access branch operations subgateway (wrapped with DryRunGitBranchOps)."""
    return DryRunGitBranchOps(self._wrapped.branch)
```

### Step 5: Implement in PrintingGit

**File: `packages/erk-shared/src/erk_shared/git/printing.py`**

```python
# Add imports
from erk_shared.git.branch_ops.abc import GitBranchOps
from erk_shared.git.branch_ops.printing import PrintingGitBranchOps

# Add property (after worktree property, ~line 41)
@property
def branch(self) -> GitBranchOps:
    """Access branch operations subgateway (wrapped with PrintingGitBranchOps)."""
    return PrintingGitBranchOps(
        self._wrapped.branch, script_mode=self._script_mode, dry_run=self._dry_run
    )
```

### Step 6: Update BranchManager to Use `git.branch`

**File: `packages/erk-shared/src/erk_shared/branch_manager/git.py`**

Remove `git_branch_ops` field, use `self.git.branch` instead:

```python
@dataclass(frozen=True)
class GitBranchManager(BranchManager):
    git: Git
    github: GitHub
    # REMOVE: git_branch_ops: GitBranchOps

    def create_branch(self, repo_root: Path, branch_name: str, base_branch: str) -> None:
        self.git.branch.create_branch(repo_root, branch_name, base_branch, force=False)
        # ... (similar changes for other methods)
```

**File: `packages/erk-shared/src/erk_shared/branch_manager/graphite.py`**

Same pattern - remove `git_branch_ops` field, use `self.git.branch`.

**File: `packages/erk-shared/src/erk_shared/branch_manager/factory.py`**

Remove `git_branch_ops` parameter:

```python
def create_branch_manager(
    *,
    git: Git,
    # REMOVE: git_branch_ops: GitBranchOps,
    github: GitHub,
    graphite: Graphite,
    graphite_branch_ops: GraphiteBranchOps | None,
) -> BranchManager:
    if isinstance(graphite, GraphiteDisabled):
        return GitBranchManager(git=git, github=github)
    # ...
```

### Step 7: Update ErkContext and Factories

**File: `packages/erk-shared/src/erk_shared/context/context.py`**

- Remove `git_branch_ops` field
- Update `branch_manager` property to not pass `git_branch_ops`

**File: `packages/erk-shared/src/erk_shared/context/factories.py`**

- Remove `git_branch_ops` from `_create_gateways()`
- Update callers

**File: `packages/erk-shared/src/erk_shared/context/testing.py`**

- Update test context factory to not require separate `git_branch_ops`

## Critical Files Summary

| File | Change |
|------|--------|
| `git/abc.py` | Add `branch` abstract property |
| `git/real.py` | Instantiate RealGitBranchOps, add property |
| `git/fake.py` | Instantiate FakeGitBranchOps, add property |
| `git/dry_run.py` | Add property wrapping with DryRunGitBranchOps |
| `git/printing.py` | Add property wrapping with PrintingGitBranchOps |
| `branch_manager/git.py` | Remove `git_branch_ops`, use `git.branch` |
| `branch_manager/graphite.py` | Remove `git_branch_ops`, use `git.branch` |
| `branch_manager/factory.py` | Remove `git_branch_ops` parameter |
| `context/context.py` | Remove `git_branch_ops` field |
| `context/factories.py` | Update gateway creation |
| `context/testing.py` | Update test factories |

## Verification

1. **Run tests**:
   ```bash
   make fast-ci  # Unit tests, type checking, linting
   ```

2. **Verify BranchManager call path**:
   - Tests in `tests/unit/branch_manager/` should pass
   - Tests in `packages/erk-shared/tests/unit/branch_manager/` should pass

3. **Integration test**:
   - `packages/erk-shared/tests/integration/test_real_git_branch_ops.py` verifies subprocess behavior

4. **Manual smoke test**:
   ```bash
   cd /workspaces/erk
   erk br checkout master  # Should work via git.branch path
   ```

## Notes

- This is a **breaking change** as designed in the objective
- All 5 GitBranchOps files already exist - we're just wiring them in
- The `branch` property follows the exact pattern of `worktree`
- Phase 2B will migrate additional branch methods from Git ABC to GitBranchOps