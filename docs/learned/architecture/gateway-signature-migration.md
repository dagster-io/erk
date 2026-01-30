---
title: Gateway Signature Migration Pattern
read_when:
  - "changing gateway method signatures (parameters or return types)"
  - "converting exception-raising methods to discriminated unions"
  - "refactoring gateway APIs"
  - "updating call sites after gateway changes"
tripwires:
  - action: "changing any gateway method signature (parameters or return type)"
    warning: "Search for ALL callers with grep BEFORE starting changes. Document the count. Missing a call site causes runtime failures. Use pattern: grep -r '.method_name(' src/ packages/ tests/"
---

# Gateway Signature Migration Pattern

A systematic approach for updating gateway method signatures and migrating all call sites atomically.

## The Challenge

Changing a gateway method signature (parameters, return type, or both) requires updates in multiple places:

1. **5 gateway implementations**: abc, real, fake, dry-run, printing
2. **N call sites**: Every place the method is invoked
3. **Tests**: Unit tests, integration tests, business logic tests

Missing a single call site causes runtime failures. This pattern prevents that.

## The 4-Phase Pattern

### Phase 1: Discover All Call Sites

Before making ANY changes, search for all callers:

```bash
# Find all call sites for the method you're changing
grep -r "\.push_to_remote\(" src/ packages/ tests/

# Count them
grep -r "\.push_to_remote\(" src/ packages/ tests/ | wc -l
```

**Document the count** in your plan or PR description. This gives you a checklist.

**Example from PR #6329:**

> Found 8 call sites for `push_to_remote` across 7 files:
>
> - `src/erk/cli/commands/admin.py` (3 calls)
> - `src/erk/cli/commands/submit.py` (2 calls)
> - `src/erk/cli/commands/pr/submit_pipeline.py` (1 call)
> - `src/erk/cli/commands/pr/sync_cmd.py` (1 call)
> - `src/erk/cli/commands/exec/scripts/rebase_with_conflict_resolution.py` (1 call)
> - `src/erk/cli/commands/exec/scripts/plan_create_review_branch.py` (1 call)
> - `packages/erk-shared/src/erk_shared/gateway/branch_manager/git.py` (1 call)

### Phase 2: Update Gateway Implementations (5 Places)

Update all 5 implementations simultaneously:

#### 1. ABC Layer

Change the abstract method signature:

```python
# Before
@abstractmethod
def push_to_remote(
    self, repo_root: Path, remote: str, refspec: str, *, set_upstream: bool, force: bool
) -> None:
    """Push to remote. Raises RuntimeError on failure."""

# After
@abstractmethod
def push_to_remote(
    self, repo_root: Path, remote: str, refspec: str, *, set_upstream: bool, force: bool
) -> PushResult | PushError:
    """Push to remote. Returns error on failure."""
```

**Key changes:**

- Return type: `-> None` → `-> PushResult | PushError`
- Docstring: "Raises" → "Returns error"

#### 2. Real Layer

Update subprocess boundary to return discriminated unions:

```python
# Before
def push_to_remote(...) -> None:
    cmd = ["git", "push", ...]
    run_subprocess_with_context(cmd, cwd=repo_root, check=True)

# After
def push_to_remote(...) -> PushResult | PushError:
    cmd = ["git", "push", ...]
    try:
        run_subprocess_with_context(cmd, cwd=repo_root, check=True)
        return PushResult()
    except subprocess.CalledProcessError as e:
        return PushError(message=str(e))
```

**Key changes:**

- Wrap subprocess in try/except
- Return success union on success
- Convert exception to error union on failure

#### 3. Fake Layer

Update to return discriminated unions:

```python
# Before
def __init__(self, *, push_raises: bool = False) -> None:
    self.push_raises = push_raises

def push_to_remote(...) -> None:
    if self.push_raises:
        raise RuntimeError("push failed")

# After
def __init__(self, *, push_to_remote_error: PushError | None = None) -> None:
    self._push_to_remote_error = push_to_remote_error

def push_to_remote(...) -> PushResult | PushError:
    if self._push_to_remote_error is not None:
        return self._push_to_remote_error
    return PushResult()
```

**Key changes:**

- Parameter: `push_raises: bool` → `push_to_remote_error: PushError | None`
- Logic: `raise` → `return error`
- Return success union on happy path

#### 4. Dry-Run Layer

Update to return success union (no-op):

```python
# Before
def push_to_remote(...) -> None:
    pass  # No-op

# After
def push_to_remote(...) -> PushResult | PushError:
    return PushResult()  # No-op, always succeeds
```

#### 5. Printing Layer

Update to delegate and return:

```python
# Before
def push_to_remote(...) -> None:
    result = self._wrapped.push_to_remote(...)
    print(f"push_to_remote(...)")
    return result

# After
def push_to_remote(...) -> PushResult | PushError:
    result = self._wrapped.push_to_remote(...)
    print(f"push_to_remote(...) -> {type(result).__name__}")
    return result
```

**Verify all 5 implementations** before proceeding to call site migration. Run type checker:

```bash
ty src/ packages/
```

### Phase 3: Migrate Each Caller

For each of the N call sites discovered in Phase 1, choose the appropriate pattern:

#### Pattern A: Fire-and-Forget (Convert Error → Exception)

For callers that don't need error reporting, convert error to exception:

```python
# Before
ctx.git.push_to_remote(repo.root, "origin", branch, set_upstream=True, force=False)
user_output("✓ Branch pushed to remote")

# After
push_result = ctx.git.push_to_remote(
    repo.root, "origin", branch, set_upstream=True, force=False
)
if isinstance(push_result, PushError):
    raise RuntimeError(push_result.message)
user_output("✓ Branch pushed to remote")
```

**When to use:**

- Caller doesn't need structured error handling
- Failure is truly exceptional (should stop execution)
- CLI commands that exit on error

#### Pattern B: Error Propagation (Return Discriminated Union)

For callers that need error reporting, propagate the discriminated union:

```python
# Before
def submit_branch(...) -> SubmitResult:
    try:
        ctx.git.push_to_remote(repo.root, "origin", branch, set_upstream=True, force=False)
    except RuntimeError as e:
        return SubmitError(error="push-failed", message=str(e))
    return SubmitSuccess(...)

# After
def submit_branch(...) -> SubmitResult | SubmitError:
    push_result = ctx.git.push_to_remote(
        repo.root, "origin", branch, set_upstream=True, force=False
    )
    if isinstance(push_result, PushError):
        if "non-fast-forward" in push_result.message:
            return SubmitError(
                error="push-rejected",
                message=f"Push rejected: {push_result.message}"
            )
        return SubmitError(error="push-failed", message=push_result.message)
    return SubmitSuccess(...)
```

**When to use:**

- Caller needs structured error reporting
- Multiple error types need different handling
- Business logic that returns discriminated unions

#### Pattern C: Ignore Errors (Optional Operations)

For optional operations where failure is acceptable:

```python
# Before (may raise, caught elsewhere)
try:
    ctx.git.push_to_remote(repo.root, "origin", branch, set_upstream=False, force=True)
except RuntimeError:
    pass  # Optional sync, ignore failures

# After (cleaner)
push_result = ctx.git.push_to_remote(
    repo.root, "origin", branch, set_upstream=False, force=True
)
if isinstance(push_result, PushError):
    # Optional sync, ignore failures
    pass
```

**When to use:**

- Best-effort operations (background sync, cleanup)
- Failures don't affect primary workflow

### Phase 4: Update Tests

Update all test files that use the changed method:

#### Unit Tests (Fakes)

Update fake configuration:

```python
# Before
fake = FakeGitRemoteOps(push_raises=True)
with pytest.raises(RuntimeError):
    fake.push_to_remote(...)

# After
fake = FakeGitRemoteOps(push_to_remote_error=PushError(message="rejected"))
result = fake.push_to_remote(...)
assert isinstance(result, PushError)
assert result.message == "rejected"
```

#### Integration Tests (Real)

Add tests for error path:

```python
def test_push_to_remote_returns_error_on_subprocess_failure() -> None:
    """Verify real implementation converts CalledProcessError to PushError."""
    ctx = create_context(dry_run=False, script_mode=True)
    repo_root = create_temp_git_repo()

    # Push to non-existent remote should fail
    result = ctx.git.remote_ops.push_to_remote(
        repo_root, "nonexistent", "main", set_upstream=False, force=False
    )

    assert isinstance(result, PushError)
    assert "fatal" in result.message.lower()
```

## Migration Checklist

Use this checklist for every gateway signature change:

### Discovery Phase

- [ ] Search for all call sites with grep
- [ ] Document call site count
- [ ] List files that will need updates

### Implementation Phase

- [ ] Update ABC method signature
- [ ] Update Real implementation
- [ ] Update Fake implementation (including constructor parameters)
- [ ] Update DryRun implementation
- [ ] Update Printing implementation
- [ ] Run type checker to verify 5-place consistency

### Migration Phase

- [ ] Migrate each call site (check off against list)
- [ ] Choose appropriate pattern (fire-and-forget, propagation, or ignore)
- [ ] Update unit tests
- [ ] Update integration tests
- [ ] Add new fake tests for discriminated unions

### Verification Phase

- [ ] Run type checker (`ty`)
- [ ] Run all tests (`pytest`)
- [ ] Grep for old method usage (should find zero in production code)
- [ ] Verify commit includes all N call sites

## Example: PR #6329 (push_to_remote and pull_rebase)

This PR demonstrates the complete pattern for two methods:

### Scope

- 2 methods: `push_to_remote`, `pull_rebase`
- 8 call sites across 7 files
- 5 gateway implementations each
- New frozen dataclasses: `PushResult`, `PushError`, `PullRebaseResult`, `PullRebaseError`

### Call Site Breakdown

- **3 fire-and-forget** (admin commands)
- **3 fire-and-forget** (submit/sync commands)
- **1 error propagation** (submit_pipeline - checks for non-fast-forward)
- **1 fire-and-forget** (plan_create_review_branch)

### Files Changed

- Types: `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py` (new)
- Gateways: 5 files (abc, real, fake, dry_run, printing)
- Callers: 7 files
- Tests: 1 new file (`tests/unit/fakes/test_fake_git_remote_ops.py`)

### Migration Time

All changes made atomically in a single commit. No intermediate broken state.

## Common Pitfalls

### ❌ WRONG: Missing Call Sites

```
# Migrated 7 of 8 call sites, forgot one
grep -r "\.push_to_remote\(" src/  # Shows 1 unmigrated site
```

**Problem**: Runtime failure when unmigrated site runs.

**Prevention**: Check off each site from discovery list.

### ❌ WRONG: Partial Gateway Updates

```python
# Updated ABC, Real, Fake, DryRun... but forgot Printing
# Type checker error: PrintingGit doesn't implement push_to_remote
```

**Problem**: Type checker catches this, but prevents progress.

**Prevention**: Update all 5 implementations before moving to call sites.

### ❌ WRONG: Mixed Try/Except and isinstance() Patterns

```python
# Inconsistent caller patterns
# File 1:
if isinstance(push_result, PushError):
    raise RuntimeError(push_result.message)

# File 2 (in same codebase):
try:
    push_result = ctx.git.push_to_remote(...)
    if isinstance(push_result, PushError):
        raise RuntimeError(push_result.message)
except RuntimeError as e:
    # Redundant try/except
```

**Problem**: Unnecessary exception handling after discriminated union check.

**Prevention**: Choose pattern A (convert to exception) OR pattern B (propagate union), not both.

## Benefits of Atomic Migration

1. **No broken intermediate state**: All call sites updated together
2. **Type checker verification**: Catches missing updates
3. **Git history clarity**: Single commit shows full change scope
4. **Easier review**: Reviewer sees complete migration pattern
5. **Safer rollback**: Single revert if needed

## Related Documentation

- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) - 5-place pattern
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Return type pattern
- [Gateway Error Boundaries](gateway-error-boundaries.md) - Where exceptions should occur
- [Parameter Naming Semantics](parameter-naming-semantics.md) - Naming fake error parameters
