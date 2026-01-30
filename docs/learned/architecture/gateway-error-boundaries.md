---
title: Gateway Error Boundaries
read_when:
  - "implementing gateway methods that call subprocess or external APIs"
  - "deciding where to place try/except blocks in gateway implementations"
  - "converting exception-based gateway methods to discriminated unions"
tripwires:
  - action: "adding try/except to fake.py, dry_run.py, or printing.py gateway implementations"
    warning: "Exception handling belongs in real.py only (at subprocess/API boundary). Fake/dry-run/printing should return discriminated union instances directly."
---

# Gateway Error Boundaries

A critical architectural pattern that defines where exception handling should occur in the 5-place gateway implementation pattern.

## The Core Principle

**try/except blocks belong in `real.py` only**, at the subprocess or API call boundary. Other implementations (fake, dry-run, printing) should return discriminated union instances directly without exception handling.

## Why This Pattern?

1. **Clean separation of concerns**: Real boundary handles external failures, fakes handle test scenarios
2. **Prevents exception leakage**: Fakes never raise exceptions—they return proper error unions
3. **Testability**: Fake implementations are trivial (no exception handling logic to test)
4. **LBYL compliance**: All layers return discriminated unions for caller inspection

## Implementation Layers

### Real Layer: Exception → Discriminated Union Conversion

The **real.py** implementation is the only place where try/except appears. It converts subprocess/API exceptions into discriminated union error types:

```python
# packages/erk-shared/src/erk_shared/gateway/git/remote_ops/real.py
def push_to_remote(
    self,
    repo_root: Path,
    remote: str,
    refspec: str,
    *,
    set_upstream: bool,
    force: bool,
) -> PushResult | PushError:
    """Push to remote. Returns error on failure."""
    cmd = ["git", "push", remote, refspec]
    if set_upstream:
        cmd.append("--set-upstream")
    if force:
        cmd.append("--force")

    try:
        run_subprocess_with_context(cmd, cwd=repo_root, check=True)
        return PushResult()
    except subprocess.CalledProcessError as e:
        # Boundary: convert exception to discriminated union
        return PushError(message=str(e))
```

**Key pattern**: The try/except wraps the subprocess call **only**. All error information is captured in the error union type.

### Fake Layer: Direct Union Return

The **fake.py** implementation returns discriminated unions directly based on configured test state:

```python
# packages/erk-shared/src/erk_shared/gateway/git/remote_ops/fake.py
class FakeGitRemoteOps(GitRemoteOps):
    def __init__(
        self,
        *,
        push_should_fail: bool = False,
        push_error_message: str = "push failed",
    ) -> None:
        self.push_should_fail = push_should_fail
        self.push_error_message = push_error_message

    def push_to_remote(
        self,
        repo_root: Path,
        remote: str,
        refspec: str,
        *,
        set_upstream: bool,
        force: bool,
    ) -> PushResult | PushError:
        """Return configured success or error union—no exceptions."""
        if self.push_should_fail:
            return PushError(message=self.push_error_message)
        return PushResult()
```

**Key pattern**: No try/except blocks. The fake returns error unions based on constructor configuration.

### Dry-Run Layer: Success-Only Return

The **dry_run.py** implementation returns success unions for all operations (no-op mutations):

```python
# packages/erk-shared/src/erk_shared/gateway/git/remote_ops/dry_run.py
def push_to_remote(
    self,
    repo_root: Path,
    remote: str,
    refspec: str,
    *,
    set_upstream: bool,
    force: bool,
) -> PushResult | PushError:
    """Dry-run always succeeds—no actual mutation occurs."""
    return PushResult()
```

**Key pattern**: No try/except, no delegation. Always returns success union.

### Printing Layer: Pass-Through Delegation

The **printing.py** implementation delegates to wrapped gateway and returns the result unchanged:

```python
# packages/erk-shared/src/erk_shared/gateway/git/remote_ops/printing.py
def push_to_remote(
    self,
    repo_root: Path,
    remote: str,
    refspec: str,
    *,
    set_upstream: bool,
    force: bool,
) -> PushResult | PushError:
    """Print the operation, then delegate to wrapped gateway."""
    result = self._wrapped.push_to_remote(
        repo_root, remote, refspec, set_upstream=set_upstream, force=force
    )
    print(f"push_to_remote({remote}, {refspec}) -> {type(result).__name__}")
    return result
```

**Key pattern**: No try/except. Delegates and returns whatever the wrapped gateway returns.

## Anti-Patterns

### ❌ WRONG: Exception Handling in Fake

```python
# DON'T DO THIS
class FakeGitRemoteOps(GitRemoteOps):
    def push_to_remote(...) -> PushResult | PushError:
        try:
            # Some test logic
            if self.should_fail:
                raise RuntimeError("fake error")
            return PushResult()
        except RuntimeError as e:
            return PushError(message=str(e))
```

**Problem**: Fakes should never raise exceptions for business logic. Return error unions directly.

### ❌ WRONG: Subprocess Calls in Fake

```python
# DON'T DO THIS
class FakeGitRemoteOps(GitRemoteOps):
    def push_to_remote(...) -> PushResult | PushError:
        try:
            subprocess.run(["git", "push", ...], check=True)
            return PushResult()
        except subprocess.CalledProcessError as e:
            return PushError(message=str(e))
```

**Problem**: Fakes should never call real subprocesses. They are in-memory test doubles.

### ❌ WRONG: Exceptions Escaping Real Layer

```python
# DON'T DO THIS
class RealGitRemoteOps(GitRemoteOps):
    def push_to_remote(...) -> PushResult | PushError:
        # Missing try/except - exception escapes!
        subprocess.run(["git", "push", ...], check=True)
        return PushResult()
```

**Problem**: Real layer must catch subprocess exceptions and convert to error unions.

## Boundary Responsibility Summary

| Layer      | Exception Handling | Returns                      |
| ---------- | ------------------ | ---------------------------- |
| **Real**   | ✅ YES             | Converts exceptions to union |
| **Fake**   | ❌ NO              | Returns union directly       |
| **DryRun** | ❌ NO              | Returns success union        |
| **Print**  | ❌ NO              | Delegates and returns        |

## Testing Strategy

### Layer 1: Fake Implementation Tests

Test that fakes return correct discriminated unions:

```python
# tests/unit/fakes/test_fake_git_remote_ops.py
def test_returns_push_result_when_success_configured() -> None:
    fake = FakeGitRemoteOps(push_should_fail=False)
    result = fake.push_to_remote(
        Path("/repo"), "origin", "main", set_upstream=False, force=False
    )
    assert isinstance(result, PushResult)

def test_returns_push_error_when_failure_configured() -> None:
    fake = FakeGitRemoteOps(push_should_fail=True, push_error_message="rejected")
    result = fake.push_to_remote(
        Path("/repo"), "origin", "main", set_upstream=False, force=False
    )
    assert isinstance(result, PushError)
    assert result.message == "rejected"
```

### Layer 2/3: Real Implementation Integration Tests

Test that real implementation converts subprocess exceptions correctly:

```python
# tests/integration/test_real_git_remote_ops.py
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

## When to Use This Pattern

Use this error boundary pattern when:

1. Gateway method calls subprocess or external API
2. Operation can fail for expected reasons (not exceptional)
3. Callers need explicit error handling
4. You want LBYL-compliant interfaces

## Migration Checklist

When converting exception-based gateway methods to discriminated unions:

1. [ ] Define frozen dataclasses for success and error types (`types.py`)
2. [ ] Update ABC to return `Result | Error` instead of raising
3. [ ] Wrap subprocess calls in real.py with try/except → return error union
4. [ ] Update fake.py to return error unions based on constructor config
5. [ ] Update dry_run.py to return success unions (no-op)
6. [ ] Update printing.py to delegate and return (no changes to logic)
7. [ ] Add Layer 1 tests for fake success/error paths
8. [ ] Update all caller sites to use `isinstance()` checks

## Reference Implementation

**PR #6329**: Convert `push_to_remote` and `pull_rebase` to discriminated unions

**Files demonstrating the pattern:**

- Types: `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py`
- Real boundary: `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/real.py`
- Fake direct return: `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/fake.py`
- Tests: `tests/unit/fakes/test_fake_git_remote_ops.py`

## Related Documentation

- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Complete pattern documentation
- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) - 5-place implementation pattern
- [Subprocess Wrappers](subprocess-wrappers.md) - How to wrap subprocess calls in gateways
