---
title: Gateway Fake Testing Exemplar
read_when:
  - "writing tests for gateway fakes with discriminated unions"
  - "implementing new fake gateway methods"
  - "testing success and error paths through fakes"
tripwires:
  - action: "creating a fake gateway without constructor-injected error configuration"
    warning: "Fakes must accept error variants at construction time (e.g., push_to_remote_error=PushError(...)) to enable failure injection in tests."
---

# Gateway Fake Testing Exemplar

`tests/unit/fakes/test_fake_git_remote_ops.py` demonstrates the canonical pattern for testing gateway fakes that return discriminated unions.

## Pattern: Configuration-Based Behavior

Fakes accept optional error variants at construction. When configured with an error, the fake returns that error instead of the success variant:

```python
# Success path (default)
ops = FakeGitRemoteOps()
result = ops.push_to_remote(cwd, "origin", "main", set_upstream=False, force=False)
assert isinstance(result, PushResult)

# Error path (configured at construction)
ops = FakeGitRemoteOps(push_to_remote_error=PushError(message="rejected"))
result = ops.push_to_remote(cwd, "origin", "main", set_upstream=False, force=False)
assert isinstance(result, PushError)
assert result.message == "rejected"
```

## Pattern: Mutation Tracking

Fakes track calls for test assertions:

```python
ops = FakeGitRemoteOps()
ops.push_to_remote(cwd, "origin", "feature", set_upstream=True, force=False)

# Assert via tracking properties
assert "feature" in ops.pushed_branches
```

For some operations, tracking occurs even on error paths:

```python
ops = FakeGitRemoteOps(pull_rebase_error=PullRebaseError(message="conflict"))
ops.pull_rebase(cwd, "origin", "main")

# Call was tracked even though it returned an error
assert len(ops.pull_rebase_calls) == 1
```

## Pattern: Discriminated Union Assertions

Tests explicitly check both variants using `isinstance()`:

```python
# Test success variant
result = ops.push_to_remote(...)
assert isinstance(result, PushResult)

# Test error variant
result = ops.push_to_remote(...)
assert isinstance(result, PushError)
assert result.message == "rejected"
```

Never use `result.success` or truthiness checks — always `isinstance()`.

## Test Organization

Fake tests are organized by operation, with separate test classes:

```
tests/unit/fakes/test_fake_git_remote_ops.py
├── TestPushToRemote       # Success, error, tracking
└── TestPullRebase         # Success, error, tracking
```

## Reference Implementation

`tests/unit/fakes/test_fake_git_remote_ops.py`:

- `TestPushToRemote` (lines 15–42): Success path, error configuration, branch tracking
- `TestPullRebase` (lines 45–68): Success path, error configuration, call tracking

## Related Documentation

- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) — FakeGateway patterns
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — The union types being tested
