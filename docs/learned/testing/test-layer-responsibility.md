---
title: Test Layer Responsibility
read_when:
  - "deciding where to test a specific behavior"
  - "responding to questions about test coverage"
  - "confused about fake tests vs integration tests vs business logic tests"
  - "wondering if behavior needs a new test"
---

# Test Layer Responsibility

How to determine which test layer should verify specific behaviors, following erk's 5-layer fake-driven testing architecture.

## The 3-Layer Model

Erk's testing strategy uses a 3-layer model:

| Layer         | Location                    | Purpose                          | Tests What                      |
| ------------- | --------------------------- | -------------------------------- | ------------------------------- |
| **Layer 1**   | `tests/unit/fakes/`         | Verify fake implementations      | Fake behavior correctness       |
| **Layer 2/3** | `tests/integration/`        | Verify real gateway integrations | Subprocess/API integration      |
| **Layer 2/3** | `tests/unit/`, `tests/e2e/` | Verify business logic            | Application behavior with fakes |

**Note**: Layer 2 (integration) and Layer 3 (business logic) often overlap in erk's test organization.

## Layer 1: Fake Implementation Tests

### Responsibility

Verify that **fake gateways behave correctly** as test doubles.

### What to Test

- Fake returns correct discriminated union types
- Fake returns configured errors when error injection is set
- Fake tracks mutations for test assertions
- Fake doesn't track mutations when returning errors (where applicable)

### Example Tests

```python
# tests/unit/fakes/test_fake_git_remote_ops.py

def test_returns_push_result_on_success(self) -> None:
    """Fake returns PushResult when no error configured."""
    ops = FakeGitRemoteOps()
    result = ops.push_to_remote(
        Path("/repo"), "origin", "main", set_upstream=False, force=False
    )
    assert isinstance(result, PushResult)

def test_returns_push_error_when_configured(self) -> None:
    """Fake returns PushError when error is injected."""
    error = PushError(message="rejected")
    ops = FakeGitRemoteOps(push_to_remote_error=error)
    result = ops.push_to_remote(
        Path("/repo"), "origin", "main", set_upstream=False, force=False
    )
    assert isinstance(result, PushError)
    assert result.message == "rejected"
```

### When NOT to Use Layer 1

- Don't test real subprocess behavior
- Don't test business logic that uses the fake
- Don't test integration between multiple gateways

## Layer 2: Integration Tests

### Responsibility

Verify that **real gateway implementations** correctly integrate with external systems (subprocess, APIs).

### What to Test

- Real implementation converts subprocess exceptions to discriminated unions
- Real implementation constructs correct subprocess commands
- Real implementation handles subprocess output correctly
- Real implementation handles subprocess errors correctly

### Example Tests

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

### When NOT to Use Layer 2

- Don't test fake behavior (use Layer 1)
- Don't test complex business logic workflows (use Layer 3)
- Don't test behavior that can be verified with fakes alone

### Integration Test Requirements

All **real.py** gateway methods with subprocess calls need integration tests:

> Before adding subprocess.run or run*subprocess_with_context calls to a gateway real.py file:
> Must add integration tests in tests/integration/test_real*\*.py. Real gateway methods with subprocess calls need tests that verify the actual subprocess behavior.

## Layer 3: Business Logic Tests

### Responsibility

Verify that **application code** (CLI commands, workflows, business logic) works correctly.

### What to Test

- CLI commands handle success paths
- CLI commands handle error paths (using fake error injection)
- Multi-step workflows coordinate multiple gateway calls
- Business logic makes correct decisions based on gateway results

### Example Tests

```python
# tests/unit/test_submit_workflow.py

def test_handles_push_rejection_gracefully() -> None:
    """Submit workflow handles non-fast-forward push errors."""
    fake_git = FakeGit()
    fake_git.remote_ops._push_to_remote_error = PushError(
        message="non-fast-forward"
    )
    ctx = create_context(git=fake_git)

    result = submit_branch(ctx, "feature-branch")

    assert isinstance(result, SubmitError)
    assert result.error == "push-rejected"
    assert "non-fast-forward" in result.message
```

### When NOT to Use Layer 3

- Don't test fake implementation details (use Layer 1)
- Don't test real subprocess integration (use Layer 2)

## Decision Tree

Use this decision tree to determine which layer should test specific behavior:

```
Q: What are you testing?

├─ Fake gateway behavior
│  └─ Layer 1: tests/unit/fakes/test_fake_<gateway>.py
│
├─ Real gateway subprocess integration
│  └─ Layer 2: tests/integration/test_real_<gateway>.py
│
└─ Business logic or CLI command
   └─ Layer 3: tests/unit/ or tests/e2e/
```

## Common Questions

### Q: Where do I test that push_to_remote returns PushError?

**A: Both Layer 1 and Layer 2, but for different reasons:**

- **Layer 1**: Test that **Fake** returns PushError when configured

  ```python
  fake = FakeGitRemoteOps(push_to_remote_error=PushError(...))
  assert isinstance(fake.push_to_remote(...), PushError)
  ```

- **Layer 2**: Test that **Real** converts subprocess failure to PushError
  ```python
  real_ctx = create_context(dry_run=False)
  result = real_ctx.git.remote_ops.push_to_remote(..., "nonexistent", ...)
  assert isinstance(result, PushError)
  ```

### Q: Do I need to test every call site that uses push_to_remote?

**A: No—test the behavior, not the plumbing:**

- **Test the decision**: If code makes a decision based on PushError (e.g., "retry" vs "abort"), test that decision
- **Don't test the delegation**: If code just forwards the result, no new test needed

**Example that needs testing:**

```python
def submit_branch(...) -> SubmitResult:
    push_result = ctx.git.push_to_remote(...)
    if isinstance(push_result, PushError):
        if "non-fast-forward" in push_result.message:
            # DECISION: special handling for non-fast-forward
            return SubmitError(error="push-rejected", ...)
    return SubmitSuccess(...)
```

**Example that doesn't need testing:**

```python
def simple_push_wrapper(...) -> PushResult | PushError:
    # Just forwards the result - no decision made
    return ctx.git.push_to_remote(...)
```

### Q: Where do I test that FakeGitRemoteOps tracks pushed branches?

**A: Layer 1 only:**

```python
# tests/unit/fakes/test_fake_git_remote_ops.py
def test_tracks_pushed_branch_on_success(self) -> None:
    ops = FakeGitRemoteOps()
    ops.push_to_remote(..., "feature", ...)
    assert ops.pushed_branches == [
        PushedBranch(remote="origin", branch="feature", ...)
    ]
```

This is fake implementation behavior, not business logic. Layer 3 tests don't need to verify tracking—they just assert on business outcomes.

### Q: Do I need fake tests AND integration tests for the same method?

**A: Yes, but they test different things:**

- **Fake tests** (Layer 1): Verify fake returns correct types and tracks mutations
- **Integration tests** (Layer 2): Verify real implementation converts subprocess behavior correctly

Both are necessary because they serve different purposes:

- Fake tests ensure test infrastructure works
- Integration tests ensure real implementation works

## Coverage Philosophy

### Don't Over-Test

If behavior is already tested at a lower layer, don't re-test at higher layers:

**❌ WRONG: Testing fake behavior in business logic tests**

```python
def test_fake_returns_push_error() -> None:
    """This belongs in Layer 1, not Layer 3."""
    fake = FakeGitRemoteOps(push_to_remote_error=PushError(...))
    assert isinstance(fake.push_to_remote(...), PushError)
```

**✓ CORRECT: Testing business logic response to errors**

```python
def test_submit_handles_push_error() -> None:
    """This is Layer 3 - testing business logic decision."""
    fake = FakeGitRemoteOps(push_to_remote_error=PushError(...))
    ctx = create_context(git=fake)
    result = submit_branch(ctx, ...)
    assert isinstance(result, SubmitError)
```

### Do Test Boundaries

Test where **control flow decisions** are made based on results:

- ✓ Test business logic that inspects error messages
- ✓ Test retry logic based on error types
- ✓ Test routing based on success/failure
- ✗ Don't test simple pass-through delegation

## Layer Boundaries in PR #6329

The git remote operations refactoring demonstrates clear layer separation:

### Layer 1 Tests

- `tests/unit/fakes/test_fake_git_remote_ops.py` (new file)
- Tests: Fake returns PushResult/PushError, tracks mutations

### Layer 2 Tests

- Existing integration tests in `tests/integration/test_real_*.py`
- Verify: Real implementation converts subprocess errors

### Layer 3 Tests

- Business logic tests already existed
- Updated to use `isinstance()` checks instead of try/except
- No new tests needed—behavior unchanged, just API style

## Anti-Patterns

### ❌ Testing Real Implementation in Fake Tests

```python
# DON'T DO THIS in tests/unit/fakes/
def test_real_converts_exceptions() -> None:
    real = RealGitRemoteOps()  # Wrong layer!
    result = real.push_to_remote(...)
```

**Problem**: Fake tests should only test fakes. Real implementation belongs in integration tests.

### ❌ Testing Fake Tracking in Business Logic Tests

```python
# DON'T DO THIS in tests/unit/
def test_submit_tracks_push() -> None:
    fake = FakeGitRemoteOps()
    ctx = create_context(git=fake)
    submit_branch(ctx, ...)
    assert len(fake.pushed_branches) == 1  # Wrong focus!
```

**Problem**: Business logic tests should assert on outcomes, not fake tracking internals.

### ❌ Duplicating Integration Tests as Fake Tests

```python
# DON'T DO THIS
def test_fake_handles_subprocess_failure() -> None:
    # Fakes don't call subprocess!
```

**Problem**: Fakes never call subprocess. This is an integration test concern.

## Related Documentation

- [Fake-Driven Testing Architecture](../testing/) - Complete testing strategy
- [Gateway Fake Testing Exemplar](gateway-fake-testing-exemplar.md) - How to write Layer 1 tests
- [Gateway Error Boundaries](../architecture/gateway-error-boundaries.md) - Where exceptions should occur
