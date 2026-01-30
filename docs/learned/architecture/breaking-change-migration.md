---
title: Breaking Change Migration Pattern
read_when:
  - "converting exception-raising methods to discriminated unions"
  - "making breaking API changes to gateway methods"
  - "refactoring method signatures across the codebase"
  - "planning large-scale API migrations"
---

# Breaking Change Migration Pattern

A systematic approach for making breaking changes to gateway APIs atomically, without creating broken intermediate states.

## When to Use This Pattern

Use this pattern when making breaking changes that affect multiple layers:

- Converting exception-raising methods → discriminated unions
- Changing method parameters (adding, removing, renaming)
- Changing return types
- Renaming gateway methods

## The No-Backwards-Compatibility Principle

**Erk explicitly rejects backwards compatibility shims** for internal APIs. When making breaking changes:

- ✅ DO: Migrate all call sites atomically in one PR
- ❌ DON'T: Add `_legacy` methods or deprecation warnings
- ❌ DON'T: Support both old and new APIs simultaneously
- ❌ DON'T: Use version flags to switch behavior

**Rationale**: Clean breaks are easier to review, maintain, and reason about than compatibility layers.

## The 5-Step Atomic Migration Pattern

### Step 1: Inventory Call Sites

Search for ALL places the method is used:

```bash
# Find all direct calls
grep -r "\.method_name\(" src/ packages/ tests/

# Find all imports (if method is standalone function)
grep -r "from .* import.*method_name" src/ packages/ tests/

# Count them
grep -r "\.method_name\(" src/ packages/ tests/ | wc -l
```

**Document the inventory**:

- Total count: X call sites
- Breakdown by file
- Breakdown by pattern (e.g., fire-and-forget vs error-reporting)

**Example from PR #6329**:

> Found 8 call sites for `push_to_remote`:
>
> - 3 in admin.py (fire-and-forget)
> - 2 in submit.py (fire-and-forget)
> - 1 in submit_pipeline.py (error-reporting with non-fast-forward check)
> - 1 in sync_cmd.py (fire-and-forget)
> - 1 in rebase_with_conflict_resolution.py (error-reporting)
> - 1 in plan_create_review_branch.py (fire-and-forget)
> - 1 in branch_manager/git.py (fire-and-forget)

### Step 2: Define New Types (If Needed)

For exception → discriminated union conversions, define frozen dataclasses:

```python
# packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py

from dataclasses import dataclass

@dataclass(frozen=True)
class PushResult:
    """Success result from pushing to remote."""

@dataclass(frozen=True)
class PushError:
    """Error result from pushing to remote. Implements NonIdealState."""
    message: str

    @property
    def error_type(self) -> str:
        return "push-failed"
```

**Guidelines**:

- Use frozen dataclasses (immutable)
- Success type can be empty if no data needed
- Error type should include `message: str` at minimum
- Consider adding `error_type` property for categorization

### Step 3: Update Gateway Implementations (5 Places)

Update all gateway layers simultaneously:

1. **ABC**: Change abstract method signature
2. **Real**: Wrap subprocess in try/except, return discriminated unions
3. **Fake**: Change constructor parameters, return discriminated unions
4. **DryRun**: Return success discriminated unions (no-op)
5. **Printing**: Update return type, delegate and return

See [Gateway Signature Migration Pattern](gateway-signature-migration.md) for detailed implementation.

**Verification**: Run type checker after Step 3:

```bash
ty src/ packages/
```

Should have zero errors before proceeding to Step 4.

### Step 4: Migrate All Call Sites

For each call site from Step 1, migrate using appropriate pattern:

#### Pattern A: Fire-and-Forget

```python
# Before
ctx.git.push_to_remote(...)

# After
push_result = ctx.git.push_to_remote(...)
if isinstance(push_result, PushError):
    raise RuntimeError(push_result.message)
```

#### Pattern B: Error Reporting

```python
# Before
try:
    ctx.git.push_to_remote(...)
except RuntimeError as e:
    return SubmitError(error="push-failed", message=str(e))

# After
push_result = ctx.git.push_to_remote(...)
if isinstance(push_result, PushError):
    return SubmitError(error="push-failed", message=push_result.message)
```

#### Pattern C: Ignore Errors

```python
# Before
try:
    ctx.git.push_to_remote(...)
except RuntimeError:
    pass

# After
push_result = ctx.git.push_to_remote(...)
if isinstance(push_result, PushError):
    pass  # Optional operation, ignore failure
```

**Check off each call site** from your Step 1 inventory as you migrate it.

### Step 5: Update Tests

Update all test files:

#### Fake Tests (Layer 1)

```python
# Before
fake = FakeGitRemoteOps(push_raises=True)
with pytest.raises(RuntimeError):
    fake.push_to_remote(...)

# After
fake = FakeGitRemoteOps(push_to_remote_error=PushError(message="rejected"))
result = fake.push_to_remote(...)
assert isinstance(result, PushError)
```

#### Business Logic Tests (Layer 3)

```python
# Before
fake = FakeGitRemoteOps(push_raises=True)
with pytest.raises(RuntimeError):
    submit_branch(ctx, ...)

# After
fake = FakeGitRemoteOps(push_to_remote_error=PushError(message="rejected"))
result = submit_branch(ctx, ...)
assert isinstance(result, SubmitError)
assert result.error == "push-failed"
```

## Atomic Commit Strategy

All changes should be in **one atomic commit**:

```bash
git add packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py  # New types
git add packages/erk-shared/src/erk_shared/gateway/git/remote_ops/*.py       # 5 gateway files
git add src/erk/cli/commands/admin.py                                        # Caller 1
git add src/erk/cli/commands/submit.py                                       # Caller 2
# ... all other callers
git add tests/unit/fakes/test_fake_git_remote_ops.py                         # New tests
git commit -m "Convert push_to_remote and pull_rebase to discriminated unions"
```

**Benefits of atomic commits**:

- No broken intermediate state
- Single revert if needed
- Clear code review
- Git bisect works correctly

## Why No Compatibility Layers?

Erk avoids backwards compatibility because:

1. **Simpler codebase**: No legacy method variants cluttering the API
2. **Clearer intent**: One way to do things, not multiple
3. **Easier review**: Reviewer sees complete migration, not partial state
4. **No confusion**: No "which method should I use?" questions
5. **Cleaner git history**: Change is atomic and complete

## Anti-Patterns

### ❌ WRONG: Adding `*_new` Method Variants

```python
# DON'T DO THIS
class Git(ABC):
    @abstractmethod
    def push_to_remote(self, ...) -> None:
        """Old version that raises."""

    @abstractmethod
    def push_to_remote_new(self, ...) -> PushResult | PushError:
        """New version with discriminated unions."""
```

**Problem**: Creates confusion, doubles API surface area, requires migration plan for cleanup.

**Correct approach**: Change signature of `push_to_remote` directly, migrate all callers.

### ❌ WRONG: Using `if old_api: ... else: ...` Flags

```python
# DON'T DO THIS
def push_to_remote(self, ..., *, use_new_api: bool = False) -> None | PushResult | PushError:
    if use_new_api:
        return self._push_new(...)
    else:
        return self._push_old(...)
```

**Problem**: Complex return type, unclear semantics, requires two implementations.

**Correct approach**: Migrate all callers to new API atomically, remove old API entirely.

### ❌ WRONG: Gradual Migration Across Multiple PRs

```
PR 1: Update gateway implementations
PR 2: Migrate 3 call sites
PR 3: Migrate 5 more call sites
PR 4: Remove old method
```

**Problem**: PRs 2-3 leave codebase in broken state (old callers don't work with new gateway).

**Correct approach**: Single PR with all changes.

## Exception: Multiple-Method Conversions

When converting multiple related methods (e.g., `push_to_remote` AND `pull_rebase`), you can do them in one atomic PR:

**PR #6329 scope**:

- 2 methods converted: `push_to_remote`, `pull_rebase`
- 4 new types: `PushResult`, `PushError`, `PullRebaseResult`, `PullRebaseError`
- 10 gateway files updated (5 per method)
- 8 call sites migrated

**Benefits**:

- Related changes grouped together
- Consistent migration pattern
- Single review for related functionality

## Verification Checklist

After making breaking changes, verify:

- [ ] All call sites from Step 1 inventory are migrated
- [ ] Type checker passes: `ty src/ packages/`
- [ ] All tests pass: `pytest`
- [ ] Grep for old API shows zero results in production code:
  ```bash
  grep -r "old_method_name\(" src/ packages/ | grep -v "test_"
  ```
- [ ] No `_legacy`, `_old`, `_new` method variants exist
- [ ] No compatibility flags or version checks
- [ ] Git history shows single atomic commit

## Real-World Example: PR #6329

### Before State

- Methods raise exceptions on failure
- Callers use try/except blocks
- 8 call sites across 7 files

### After State

- Methods return discriminated unions
- Callers use isinstance() checks
- All 8 call sites migrated atomically

### Migration Stats

- Files changed: 18
- Gateway implementations: 10 (5 per method)
- Call sites migrated: 8
- New types added: 4
- New test files: 1
- Backwards compatibility methods: 0

### Commit Message

```
Convert push_to_remote and pull_rebase to discriminated unions

BREAKING CHANGE: Both methods now return Result | Error instead of raising exceptions.

Updated:
- 10 gateway implementations (abc, real, fake, dry_run, printing for each)
- 8 call sites across 7 files
- Added comprehensive fake tests

See docs/learned/architecture/discriminated-union-error-handling.md for pattern details.
```

## Related Documentation

- [Gateway Signature Migration Pattern](gateway-signature-migration.md) - Detailed migration steps
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Pattern documentation
- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) - 5-place pattern
- [Gateway Error Boundaries](gateway-error-boundaries.md) - Where exceptions belong
