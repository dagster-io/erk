---
title: Gateway Fake Testing Exemplar
read_when:
  - "writing tests for gateway fake implementations"
  - "testing discriminated union return types in fakes"
  - "verifying fake behavior for success and error paths"
  - "testing mutation tracking in fake gateways"
---

# Gateway Fake Testing Exemplar

How to test fake gateway implementations that return discriminated unions, using `test_fake_git_remote_ops.py` as the canonical reference.

## Purpose of Fake Tests

Fake gateway tests verify that:

1. **Success path**: Fake returns success discriminated union
2. **Error path**: Fake returns configured error discriminated union
3. **Mutation tracking**: Fake records method calls for test assertions
4. **Error isolation**: Fake doesn't track mutations when returning errors (where applicable)

## Test Structure Pattern

Organize tests by method, with separate classes for each gateway method:

```python
"""Tests for FakeGitRemoteOps."""

from pathlib import Path

from erk_shared.gateway.git.remote_ops.fake import FakeGitRemoteOps
from erk_shared.gateway.git.remote_ops.types import (
    PullRebaseError,
    PullRebaseResult,
    PushError,
    PushResult,
)


class TestPushToRemote:
    """Tests for push_to_remote method."""

    def test_returns_push_result_on_success(self) -> None:
        """Default fake returns success."""
        ...

    def test_returns_push_error_when_configured(self) -> None:
        """Fake returns configured error."""
        ...

    def test_tracks_pushed_branch_on_success(self) -> None:
        """Fake records successful mutations."""
        ...

    def test_does_not_track_pushed_branch_on_error(self) -> None:
        """Fake doesn't record failed mutations."""
        ...


class TestPullRebase:
    """Tests for pull_rebase method."""
    ...
```

**Key organizational patterns:**

- One test class per gateway method
- Descriptive test method names (what behavior is verified)
- Docstrings explain the test's purpose
- Import only the types needed for that test file

## Testing Success Path

Verify that default fake (no error configured) returns success discriminated union:

```python
def test_returns_push_result_on_success(self) -> None:
    """Fake returns PushResult when no error configured."""
    ops = FakeGitRemoteOps()  # No error injection
    result = ops.push_to_remote(
        Path("/repo"), "origin", "main", set_upstream=False, force=False
    )
    assert isinstance(result, PushResult)
```

**Pattern details:**

- Use `isinstance()` to verify discriminated union type
- Don't assert on result fields if success type is empty (like `PushResult`)
- Use realistic parameter values (Path objects, not strings)

## Testing Error Path

Verify that fake returns configured error discriminated union:

```python
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

**Pattern details:**

- Create error instance with specific message
- Pass error via constructor parameter (following `*_error` naming convention)
- Verify both type and error content (message field)
- Use descriptive error messages that make test intent clear

## Testing Mutation Tracking (Success)

Verify that fake records successful method calls for later assertions:

```python
def test_tracks_pushed_branch_on_success(self) -> None:
    """Fake records push details when successful."""
    ops = FakeGitRemoteOps()
    ops.push_to_remote(
        Path("/repo"), "origin", "feature", set_upstream=True, force=False
    )
    assert ops.pushed_branches == [
        PushedBranch(
            remote="origin",
            branch="feature",
            set_upstream=True,
            force=False
        )
    ]
```

**Pattern details:**

- Call method with specific parameters
- Assert on fake's tracking property (e.g., `pushed_branches`)
- Use frozen dataclass for tracked data (matches gateway parameters)
- Verify complete parameter set (don't skip optional params)

## Testing Mutation Isolation (Error)

Verify that fake doesn't track mutations when returning errors:

```python
def test_does_not_track_pushed_branch_on_error(self) -> None:
    """Fake doesn't record push when error occurs."""
    ops = FakeGitRemoteOps(push_to_remote_error=PushError(message="rejected"))
    ops.push_to_remote(
        Path("/repo"), "origin", "main", set_upstream=False, force=False
    )
    assert ops.pushed_branches == []
```

**When to use this pattern:**

- Mutations that have side effects (creating resources)
- Operations where "attempt" vs "success" matters
- Not needed for read-only operations

**When NOT to track on error:**

Some operations should track calls even on error (e.g., pull_rebase tracks all attempts):

```python
def test_tracks_pull_rebase_call_even_on_error(self) -> None:
    """pull_rebase tracks all calls regardless of success/error."""
    cwd = Path("/repo")
    ops = FakeGitRemoteOps(pull_rebase_error=PullRebaseError(message="conflict"))
    ops.pull_rebase(cwd, "origin", "main")
    assert ops.pull_rebase_calls == [(cwd, "origin", "main")]
```

**Decision criteria**: Track on error if:

- Tests need to verify "attempted" count
- Operation is read-like (doesn't create state)
- Failure is expected and needs verification

## Fake Implementation Pattern

The fake must support all test patterns above:

```python
class FakeGitRemoteOps(GitRemoteOps):
    def __init__(
        self,
        *,
        push_to_remote_error: PushError | None = None,
        pull_rebase_error: PullRebaseError | None = None,
    ) -> None:
        """Configure fake with error injection."""
        self._push_to_remote_error = push_to_remote_error
        self._pull_rebase_error = pull_rebase_error

        # Mutation tracking
        self._pushed_branches: list[PushedBranch] = []
        self._pull_rebase_calls: list[tuple[Path, str, str]] = []

    def push_to_remote(
        self,
        repo_root: Path,
        remote: str,
        refspec: str,
        *,
        set_upstream: bool,
        force: bool,
    ) -> PushResult | PushError:
        """Return configured error or success, track only on success."""
        if self._push_to_remote_error is not None:
            return self._push_to_remote_error

        # Track successful mutation
        self._pushed_branches.append(
            PushedBranch(
                remote=remote,
                branch=refspec,
                set_upstream=set_upstream,
                force=force,
            )
        )
        return PushResult()

    def pull_rebase(
        self, cwd: Path, remote: str, branch: str
    ) -> PullRebaseResult | PullRebaseError:
        """Return configured error or success, track all calls."""
        # Track all calls (even errors)
        self._pull_rebase_calls.append((cwd, remote, branch))

        if self._pull_rebase_error is not None:
            return self._pull_rebase_error
        return PullRebaseResult()

    # Read-only properties for test assertions
    @property
    def pushed_branches(self) -> list[PushedBranch]:
        """Return tracked push operations (read-only)."""
        return self._pushed_branches

    @property
    def pull_rebase_calls(self) -> list[tuple[Path, str, str]]:
        """Return tracked pull rebase calls (read-only)."""
        return self._pull_rebase_calls
```

**Implementation requirements:**

1. Constructor accepts `*_error` parameters for each method
2. Private fields store tracking data (`_pushed_branches`, etc.)
3. Methods check error config and return early if set
4. Methods track mutations (conditionally or always)
5. Read-only properties expose tracking data for assertions

## Test File Location

Place fake tests in `tests/unit/fakes/`:

```
tests/unit/fakes/
├── test_fake_git_remote_ops.py
├── test_fake_git_branch_ops.py
├── test_fake_github_issues.py
└── ...
```

**Naming convention**: `test_fake_<gateway>_<subgateway>.py`

## Complete Reference Example

See `tests/unit/fakes/test_fake_git_remote_ops.py` (PR #6329) for the complete pattern:

**Tested behaviors:**

- `push_to_remote` success → returns `PushResult`
- `push_to_remote` error → returns `PushError`
- `push_to_remote` success → tracks in `pushed_branches`
- `push_to_remote` error → does NOT track
- `pull_rebase` success → returns `PullRebaseResult`
- `pull_rebase` error → returns `PullRebaseError`
- `pull_rebase` success → tracks call
- `pull_rebase` error → STILL tracks call

**Why this is the exemplar:**

1. Demonstrates discriminated union testing (both variants)
2. Shows mutation tracking with frozen dataclass
3. Shows conditional tracking (push) vs always tracking (pull)
4. Clear test organization with separate classes per method
5. Complete coverage: success path, error path, tracking behavior

## Comparison with Integration Tests

| Aspect              | Fake Tests (Layer 1)             | Integration Tests (Layer 2/3)      |
| ------------------- | -------------------------------- | ---------------------------------- |
| **Purpose**         | Verify fake behavior correctness | Verify real subprocess integration |
| **What's tested**   | Fake returns correct union types | Real converts exceptions to unions |
| **Dependencies**    | Zero (pure Python)               | Git/GitHub/Graphite installed      |
| **Speed**           | Instant (microseconds)           | Slow (subprocess overhead)         |
| **Location**        | `tests/unit/fakes/`              | `tests/integration/`               |
| **Test assertions** | `isinstance(result, PushError)`  | Actual subprocess behavior         |

## Anti-Patterns

### ❌ WRONG: Testing Real Implementation in Fake Tests

```python
# DON'T DO THIS - tests the wrong layer
def test_push_to_remote_calls_subprocess(self) -> None:
    ops = RealGitRemoteOps()  # Should use Fake in fake tests!
    result = ops.push_to_remote(...)
```

Fake tests should only test fakes. Real implementation testing belongs in integration tests.

### ❌ WRONG: Not Testing Error Path

```python
# INCOMPLETE - missing error path test
class TestPushToRemote:
    def test_returns_push_result_on_success(self) -> None:
        ops = FakeGitRemoteOps()
        result = ops.push_to_remote(...)
        assert isinstance(result, PushResult)

    # Missing: test_returns_push_error_when_configured
```

Every discriminated union method needs both success and error tests.

### ❌ WRONG: Using `assert result.success` Instead of `isinstance()`

```python
# DON'T DO THIS - loses type narrowing
def test_returns_error(self) -> None:
    ops = FakeGitRemoteOps(push_to_remote_error=PushError(message="rejected"))
    result = ops.push_to_remote(...)
    assert not result.success  # Assumes a "success" field - wrong pattern!
```

Discriminated unions use `isinstance()`, not boolean flags.

## Checklist for Writing Fake Tests

When adding tests for a new fake implementation:

1. [ ] Create test file in `tests/unit/fakes/test_fake_<gateway>.py`
2. [ ] Import discriminated union types (Result and Error)
3. [ ] Create test class per gateway method
4. [ ] Test success path: default fake returns success union
5. [ ] Test error path: configured fake returns error union
6. [ ] Test mutation tracking: fake records calls/parameters
7. [ ] Test error isolation: fake doesn't track when returning error (if applicable)
8. [ ] Use `isinstance()` checks for discriminated unions
9. [ ] Assert on error content (e.g., `message` field)
10. [ ] Use realistic parameter values (Path objects, not strings)

## Related Documentation

- [Fake-Driven Testing Architecture](../testing/) - Overall testing strategy
- [Gateway Error Boundaries](../architecture/gateway-error-boundaries.md) - Where exceptions should occur
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) - Return type pattern
- [Parameter Naming Semantics](../architecture/parameter-naming-semantics.md) - `*_error` parameter convention
