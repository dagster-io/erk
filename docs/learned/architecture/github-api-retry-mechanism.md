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
last_audited: "2026-02-16 14:05 PT"
audit_result: clean
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
- `unexpected end of json input` — occurs when GitHub API returns truncated JSON responses

See `erk_shared/gateway/github/transient_errors.py` for the canonical pattern list.

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

## Workflow Run Polling Strategy

The `poll_for_workflow_run()` method reuses `with_retries` for a different purpose: polling for a workflow run to appear. Unlike transient error retry (where the same call might succeed on retry), polling repeatedly queries the API until the expected data appears.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py, RealGitHub.poll_for_workflow_run -->

See `RealGitHub.poll_for_workflow_run()` in `real.py` for the implementation.

**Configuration**: `retry_delays=[float(poll_interval)] * max_attempts` where defaults are `poll_interval=2` and `timeout=30`, yielding 15 attempts at 2-second intervals. The callback returns `RetryRequested` when the run hasn't appeared yet and returns the run ID string on success.

**Distinction from transient error retry**: Transient error retry uses exponential backoff (`[0.5, 1.0]`) for network failures. Polling uses uniform intervals for data that hasn't materialized yet. Both use `with_retries` but serve different purposes.

## Implementation Reference

| File                                            | Purpose                                                |
| ----------------------------------------------- | ------------------------------------------------------ |
| `erk_shared/subprocess_utils.py`                | `execute_gh_command_with_retry()`                      |
| `erk_shared/gateway/github/retry.py`            | `with_retries()`, `RetryRequested`, `RetriesExhausted` |
| `erk_shared/gateway/github/transient_errors.py` | `is_transient_error()`                                 |

## Related Documentation

- [Subprocess Wrappers](subprocess-wrappers.md) - Base subprocess execution patterns
- [GitHub API Rate Limits](github-api-rate-limits.md) - Rate limit handling (separate from retry)
- [Erk Architecture Patterns](erk-architecture.md) - Time abstraction and dependency injection
