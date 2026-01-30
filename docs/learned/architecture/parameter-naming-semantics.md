---
title: Parameter Naming Semantics
read_when:
  - "designing fake gateway constructor parameters for error injection"
  - "converting exception-raising methods to discriminated unions"
  - "naming parameters that configure test behavior"
---

# Parameter Naming Semantics

A naming convention that signals the error handling semantics of gateway methods through parameter suffixes.

## The Pattern

Parameter names communicate whether a method returns discriminated unions or raises exceptions:

| Suffix     | Meaning                                      | Example                                   |
| ---------- | -------------------------------------------- | ----------------------------------------- |
| `*_error`  | Method returns `Result \| Error` union       | `push_to_remote_error: PushError \| None` |
| `*_raises` | Method raises exception (deprecated pattern) | `fetch_raises: bool` (legacy)             |
| No suffix  | Success-only or method doesn't fail          | `current_branch: str`                     |

## Why This Convention?

1. **Self-documenting**: Parameter name immediately tells you the method's error contract
2. **Migration clarity**: When converting exceptions → unions, rename `*_raises` → `*_error`
3. **Consistent with return types**: `*_error` parameter → returns `SomeError` type
4. **Test readability**: `FakeGit(push_to_remote_error=PushError(...))` is clear

## Fake Gateway Constructor Pattern

When configuring fake gateways to return errors, use the `*_error` suffix:

```python
class FakeGitRemoteOps(GitRemoteOps):
    def __init__(
        self,
        *,
        push_to_remote_error: PushError | None = None,
        pull_rebase_error: PullRebaseError | None = None,
    ) -> None:
        """Configure fake with error injection.

        Args:
            push_to_remote_error: PushError to return when push_to_remote() is called
            pull_rebase_error: PullRebaseError to return when pull_rebase() is called
        """
        self._push_to_remote_error = push_to_remote_error
        self._pull_rebase_error = pull_rebase_error

    def push_to_remote(
        self,
        repo_root: Path,
        remote: str,
        refspec: str,
        *,
        set_upstream: bool,
        force: bool,
    ) -> PushResult | PushError:
        """Return configured error or success."""
        if self._push_to_remote_error is not None:
            return self._push_to_remote_error
        return PushResult()
```

**Key points:**

- Parameter type is `ErrorType | None` (optional error injection)
- Parameter name matches method name + `_error` suffix
- Docstring clarifies: "PushError to return when push_to_remote() is called"

## Test Usage Pattern

The naming convention makes test setup self-documenting:

```python
def test_handles_push_rejection() -> None:
    """Test that push rejection is handled gracefully."""
    fake = FakeGitRemoteOps(
        push_to_remote_error=PushError(message="non-fast-forward")
    )

    result = fake.push_to_remote(
        Path("/repo"), "origin", "main", set_upstream=False, force=False
    )

    assert isinstance(result, PushError)
    assert "non-fast-forward" in result.message
```

**Contrast with exception-raising pattern (deprecated):**

```python
# OLD PATTERN - less clear, boolean doesn't capture error message
def test_handles_push_rejection_old() -> None:
    fake = FakeGitRemoteOps(push_to_remote_raises=True)  # What error? What message?
    with pytest.raises(RuntimeError):
        fake.push_to_remote(...)
```

## Migration Pattern: Exceptions → Discriminated Unions

When converting gateway methods from exceptions to discriminated unions, follow this renaming:

### Step 1: Before (Exception-Based)

```python
class FakeGitHub(GitHub):
    def __init__(
        self,
        *,
        pr_diff_raises: bool = False,  # Boolean: does it raise?
    ) -> None:
        self.pr_diff_raises = pr_diff_raises

    def get_pr_diff(self, repo_root: Path, pr_number: int) -> str:
        """Get PR diff. Raises RuntimeError on failure."""
        if self.pr_diff_raises:
            raise RuntimeError("PR diff unavailable")
        return "diff content"
```

### Step 2: After (Discriminated Union)

```python
class FakeGitHub(GitHub):
    def __init__(
        self,
        *,
        pr_diff_error: PRDiffError | None = None,  # Error instance to return
    ) -> None:
        self._pr_diff_error = pr_diff_error

    def get_pr_diff(
        self, repo_root: Path, pr_number: int
    ) -> PRDiff | PRDiffError:
        """Get PR diff. Returns PRDiffError on failure."""
        if self._pr_diff_error is not None:
            return self._pr_diff_error
        return PRDiff(content="diff content")
```

**Migration checklist:**

1. Rename parameter: `*_raises: bool` → `*_error: ErrorType | None`
2. Change logic: `if self.flag: raise` → `if self._error: return self._error`
3. Update method signature: `-> T` → `-> T | ErrorType`
4. Update all test call sites to pass error instances

## Alternative Error Configuration Patterns

Some fakes use separate boolean and message parameters for backward compatibility:

```python
class FakeGitRemoteOps(GitRemoteOps):
    def __init__(
        self,
        *,
        push_should_fail: bool = False,
        push_error_message: str = "push failed",
    ) -> None:
        self.push_should_fail = push_should_fail
        self.push_error_message = push_error_message

    def push_to_remote(...) -> PushResult | PushError:
        if self.push_should_fail:
            return PushError(message=self.push_error_message)
        return PushResult()
```

**When to use this pattern:**

- Transitional phase during migration (support old tests)
- Error type has multiple fields beyond `message`
- Need to vary error messages dynamically in tests

**Preferred pattern for new code:**

Pass error instance directly:

```python
FakeGitRemoteOps(
    push_to_remote_error=PushError(message="custom error message")
)
```

## Examples in the Codebase

### Git Remote Operations

`packages/erk-shared/src/erk_shared/gateway/git/remote_ops/fake.py`:

```python
def __init__(
    self,
    *,
    push_to_remote_error: PushError | None = None,
    pull_rebase_error: PullRebaseError | None = None,
) -> None:
    ...
```

### GitHub Issues Gateway

`packages/erk-shared/src/erk_shared/gateway/github/issues/fake.py`:

```python
def __init__(
    self,
    *,
    add_reaction_error: str | None = None,
    get_comments_error: str | None = None,
) -> None:
    ...
```

**Note**: Some older fakes use `str | None` for error messages instead of typed error instances. Prefer typed instances for new code.

## Naming Convention Summary

| Pattern                                  | Use When                                       | Example                                   |
| ---------------------------------------- | ---------------------------------------------- | ----------------------------------------- |
| `method_name_error: ErrorType \| None`   | Method returns discriminated union (preferred) | `push_to_remote_error: PushError \| None` |
| `method_name_raises: bool`               | Legacy exception-based pattern (deprecated)    | `fetch_raises: bool`                      |
| `method_should_fail: bool` + `*_message` | Transitional or multi-field errors             | `push_should_fail: bool`                  |

## Related Documentation

- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Complete pattern documentation
- [Gateway Error Boundaries](gateway-error-boundaries.md) - Where exception handling should occur
- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) - 5-place pattern with fakes
