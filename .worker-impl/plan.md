# Plan: Phase 4 — Git Branch/Worktree Creation Failures → Discriminated Unions

**Part of Objective #6292, Steps 4.1–4.4**

Convert `create_branch` and `add_worktree` from `None`-returning, exception-raising methods to discriminated union return types (`BranchCreated | BranchCreateError` and `WorktreeAdded | WorktreeAddError`).

## Reference Pattern

Follow the Phase 3 pattern (PR #6329) established in `git/remote_ops/types.py`:
- Success type: empty frozen dataclass
- Error type: frozen dataclass with `message: str` and `error_type` property implementing `NonIdealState`

## Step 4.1: Define Types

### New file: `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/types.py`

```python
@dataclass(frozen=True)
class BranchCreated:
    """Success result from creating a branch."""

@dataclass(frozen=True)
class BranchCreateError:
    """Error result from creating a branch. Implements NonIdealState."""
    message: str

    @property
    def error_type(self) -> str:
        return "branch-create-failed"
```

### New file: `packages/erk-shared/src/erk_shared/gateway/git/worktree/types.py`

```python
@dataclass(frozen=True)
class WorktreeAdded:
    """Success result from adding a worktree."""

@dataclass(frozen=True)
class WorktreeAddError:
    """Error result from adding a worktree. Implements NonIdealState."""
    message: str

    @property
    def error_type(self) -> str:
        return "worktree-add-failed"
```

## Step 4.2: Update `create_branch` Across 5 Implementations

All in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/`:

| File | Change |
|------|--------|
| `abc.py:25` | Return type `None` → `BranchCreated \| BranchCreateError` |
| `real.py:29` | Wrap `run_subprocess_with_context` in try/except, return `BranchCreated()` or `BranchCreateError(message=str(e))` |
| `fake.py:106` | Return `BranchCreated()`, add constructor param `create_branch_error: BranchCreateError \| None` for test injection |
| `dry_run.py:32` | Return `BranchCreated()` (no-op success) |
| `printing.py:27` | Return result from `self._wrapped.create_branch(...)` |

## Step 4.3: Update `add_worktree` Across 5 Implementations

All in `packages/erk-shared/src/erk_shared/gateway/git/worktree/`:

| File | Change |
|------|--------|
| `abc.py:31` | Return type `None` → `WorktreeAdded \| WorktreeAddError` |
| `real.py:59` | Wrap `run_subprocess_with_context` in try/except, return `WorktreeAdded()` or `WorktreeAddError(message=str(e))` |
| `fake.py:85` | Return `WorktreeAdded()`, add constructor param `add_worktree_error: WorktreeAddError \| None` for test injection |
| `dry_run.py:60` | Return `WorktreeAdded()` (no-op success) |
| `printing.py:55` | Return result from `self._wrapped.add_worktree(...)` |

## Step 4.4: Update BranchManager and All Callers

### BranchManager Layer (4 files)

The `BranchManager.create_branch()` also needs updated return type:

| File | Change |
|------|--------|
| `branch_manager/abc.py:42` | Return type `None` → `BranchCreated \| BranchCreateError` |
| `branch_manager/graphite.py:68` | Complex — calls `git.branch.create_branch()` 3 times (lines 86, 135, 147). Must check each result and propagate errors. Return `BranchCreated()` at the end on success. |
| `branch_manager/git.py:64` | Return result from `self.git.branch.create_branch(...)` |
| `branch_manager/fake.py:59` | Return `BranchCreated()`, add constructor param for error injection |

### Production Callers of `BranchManager.create_branch()` (~7 call sites)

Each caller currently ignores the `None` return. Update to check for error:

| File | Call Site |
|------|-----------|
| `src/erk/cli/commands/branch/create_cmd.py:168` | `ctx.branch_manager.create_branch(...)` |
| `src/erk/cli/commands/wt/create_cmd.py:690` | `ctx.branch_manager.create_branch(...)` |
| `src/erk/cli/commands/stack/consolidate_cmd.py:308` | `ctx.branch_manager.create_branch(...)` |
| `src/erk/cli/commands/slot/unassign_cmd.py:76` | `ctx.branch_manager.create_branch(...)` |
| `src/erk/cli/commands/slot/init_pool_cmd.py:107` | `ctx.branch_manager.create_branch(...)` |
| `src/erk/cli/commands/submit.py:702` | `ctx.branch_manager.create_branch(...)` |
| `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py:139` | `branch_manager.create_branch(...)` |

Pattern for each caller:
```python
result = ctx.branch_manager.create_branch(repo.root, branch_name, base)
if isinstance(result, BranchCreateError):
    user_output(f"Error creating branch: {result.message}")
    raise SystemExit(1)
```

### Direct Caller of `git.branch.create_branch()` (1 call site)

| File | Call Site |
|------|-----------|
| `src/erk/cli/commands/exec/scripts/plan_create_review_branch.py:168` | Direct gateway call |

### Production Callers of `git.worktree.add_worktree()` (~11 call sites)

| File | Call Site |
|------|-----------|
| `src/erk/cli/commands/stack/consolidate_cmd.py:313` | |
| `src/erk/cli/commands/stack/split_old/plan.py:207` | |
| `src/erk/cli/commands/stack/move_cmd.py:149` | |
| `src/erk/cli/commands/checkout_helpers.py:192` | |
| `src/erk/cli/commands/wt/create_cmd.py:271,326,330,334` | 4 call sites |
| `src/erk/cli/commands/slot/common.py:547,559` | 2 call sites |
| `src/erk/cli/commands/slot/init_pool_cmd.py:117` | |

Pattern for each caller:
```python
result = ctx.git.worktree.add_worktree(...)
if isinstance(result, WorktreeAddError):
    user_output(f"Error adding worktree: {result.message}")
    raise SystemExit(1)
```

## Test Updates

### Unit Tests
- Update `tests/unit/fakes/test_fake_git.py` for new return types
- Verify fake error injection works for both methods

### Integration Tests
- Update `tests/integration/test_real_git_branch_ops.py` — verify `BranchCreated` returned on success
- Update `tests/integration/test_real_git.py` — verify `WorktreeAdded` returned on success
- Update `tests/integration/test_dryrun_integration.py` — verify success types from dry-run

## File Change Summary

| Category | Files | Count |
|----------|-------|-------|
| New type files | `branch_ops/types.py`, `worktree/types.py` | 2 |
| Gateway implementations | abc, real, fake, dry_run, printing × 2 methods | 10 |
| BranchManager layer | abc, graphite, git, fake | 4 |
| Production callers (create_branch) | 7 CLI commands + 1 exec script | 8 |
| Production callers (add_worktree) | 7 CLI commands (11 call sites) | 7 |
| Tests | ~4 test files | 4 |
| **Total** | | **~35** |

## Verification

1. Run `ty` for type checking across all modified files
2. Run unit tests: `pytest tests/unit/` — verify fakes work with new return types
3. Run integration tests: `pytest tests/integration/test_real_git_branch_ops.py tests/integration/test_real_git.py` — verify real implementations return correct types
4. Verify no remaining `None` return annotations on the converted methods via grep