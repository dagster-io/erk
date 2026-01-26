---
title: GitHub API Retry Mechanism
read_when:
  - "implementing GitHub API calls with retry logic"
  - "handling transient network errors"
  - "using execute_gh_command_with_retry()"
  - "injecting Time for testable retry delays"
tripwires:
  - action: "calling execute_gh_command() instead of execute_gh_command_with_retry() for network-sensitive operations"
    warning: "Use `execute_gh_command_with_retry()` for operations that may fail due to transient network errors. Pass `time_impl` for testability."
  - action: "checking isinstance after RetriesExhausted without type narrowing"
    warning: "After checking `isinstance(result, RetriesExhausted)`, the else branch is type-narrowed to the success type. Use `assert isinstance(result, T)` if needed for clarity."
---

# GitHub API Retry Mechanism

Erk includes a retry mechanism for GitHub API calls that handles transient network errors automatically. This document explains the pattern, when to use it, and how to test it.

## The Problem

GitHub API calls can fail due to transient network issues:

- I/O timeouts
- Connection refused
- Network unreachable
- Connection reset

These errors are typically recoverable with a simple retry after a short delay.

## The Solution: execute_gh_command_with_retry()

The `execute_gh_command_with_retry()` function wraps `execute_gh_command()` with automatic retry logic:

```python
from erk_shared.subprocess_utils import execute_gh_command_with_retry

# With retry (recommended for network-sensitive operations)
result = execute_gh_command_with_retry(cmd, cwd, time_impl)
```

### Default Behavior

- **Retry delays**: `[0.5, 1.0]` seconds (exponential backoff)
- **Max attempts**: 3 (initial + 2 retries)
- **Transient errors**: Network timeouts, connection failures, TCP errors

### Transient Error Detection

Errors are detected as transient by checking for patterns in the error message:

- `i/o timeout`
- `dial tcp`
- `connection refused`
- `could not connect`
- `network is unreachable`
- `connection reset`
- `connection timed out`

See `erk_shared/github/transient_errors.py` for the canonical pattern list.

## The with_retries Pattern

The retry mechanism uses a return-value control flow pattern via `with_retries()`:

```python
from erk_shared.gateway.github.retry import with_retries, RetryRequested, RetriesExhausted

def fetch_with_retry() -> str | RetryRequested:
    try:
        return api.fetch_data()
    except RuntimeError as e:
        if is_transient_error(str(e)):
            return RetryRequested(reason=str(e))
        raise  # Non-transient errors bubble up immediately

result = with_retries(time_impl, "fetch data", fetch_with_retry)

if isinstance(result, RetriesExhausted):
    # Handle failure after all retries
    raise RuntimeError(f"Failed: {result.reason}")

# result is now type-narrowed to str
use_data(result)
```

### Key Types

| Type               | Purpose                                           |
| ------------------ | ------------------------------------------------- |
| `RetryRequested`   | Callback signals "try again" (transient failure)  |
| `RetriesExhausted` | `with_retries` signals "gave up after N attempts" |

### Control Flow

1. Callback returns success value → `with_retries` returns immediately
2. Callback returns `RetryRequested` → Sleep, then retry
3. Callback raises exception → Exception bubbles up immediately (permanent failure)
4. All retries exhausted → Returns `RetriesExhausted`

## Rate Limits Are NOT Retried

The retry mechanism handles **transient network errors**, not **rate limits**.

| Error Type       | Example                    | Retried? |
| ---------------- | -------------------------- | -------- |
| Network timeout  | `dial tcp: i/o timeout`    | Yes      |
| Connection reset | `connection reset by peer` | Yes      |
| Rate limit       | `API rate limit exceeded`  | No       |
| Auth failure     | `401 Unauthorized`         | No       |
| Not found        | `404 Not Found`            | No       |

For rate limit issues, see [GitHub API Rate Limits](github-api-rate-limits.md).

## Time Injection for Testability

The retry mechanism requires a `Time` implementation for sleep operations:

```python
# Production code
from erk_shared.gateway.time.real import RealTime
execute_gh_command_with_retry(cmd, cwd, RealTime())

# Test code
from erk_shared.gateway.time.fake import FakeTime
fake_time = FakeTime()
execute_gh_command_with_retry(cmd, cwd, fake_time)
assert fake_time.sleep_calls == [0.5, 1.0]  # Verify retry delays
```

### Why Inject Time?

- Tests complete instantly (no actual sleeping)
- Tests can verify exact retry delays
- Consistent with erk's dependency injection pattern

See [Erk Architecture Patterns](erk-architecture.md#time-abstraction-for-testing) for the full Time abstraction guide.

## Implementation Reference

| File                                    | Purpose                                                |
| --------------------------------------- | ------------------------------------------------------ |
| `erk_shared/subprocess_utils.py`        | `execute_gh_command_with_retry()`                      |
| `erk_shared/github/retry.py`            | `with_retries()`, `RetryRequested`, `RetriesExhausted` |
| `erk_shared/github/transient_errors.py` | `is_transient_error()`                                 |

## Related Documentation

- [Subprocess Wrappers](subprocess-wrappers.md) - Base subprocess execution patterns
- [GitHub API Rate Limits](github-api-rate-limits.md) - Rate limit handling (separate from retry)
- [Erk Architecture Patterns](erk-architecture.md) - Time abstraction and dependency injection
