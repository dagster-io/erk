---
title: Time Injection Testing Patterns
read_when:
  - "writing time-dependent tests"
  - "using FakeTime in tests"
  - "fixing flaky timestamp tests"
  - "calling datetime.now() or time.sleep() in erk code"
tripwires:
  - action: "importing time or calling datetime.now() directly"
    warning: "Never import time directly or call datetime.now(). Use ctx.time.now() and ctx.time.sleep() for testability. Read this doc."
  - action: "writing a test that depends on the current time"
    warning: "Use FakeTime from context_for_test(). The default fake time is datetime(2024, 1, 15, 14, 30, 0)."
---

# Time Injection Testing Patterns

Erk uses a time gateway abstraction to make time-dependent code testable. All time operations go through `ctx.time` instead of direct `datetime.now()` or `time.sleep()` calls.

## Time Gateway ABC

<!-- Source: packages/erk-shared/src/erk_shared/gateway/time/abc.py -->

The `Time` ABC at `packages/erk-shared/src/erk_shared/gateway/time/abc.py` defines three abstract methods:

| Method        | Signature                  | Purpose                                       |
| ------------- | -------------------------- | --------------------------------------------- |
| `now()`       | `-> datetime`              | Current time (replaces `datetime.now()`)      |
| `sleep()`     | `(seconds: float) -> None` | Sleep (replaces `time.sleep()`)               |
| `monotonic()` | `-> float`                 | Monotonic clock (replaces `time.monotonic()`) |

## FakeTime

<!-- Source: packages/erk-shared/src/erk_shared/gateway/time/fake.py -->

`FakeTime` at `packages/erk-shared/src/erk_shared/gateway/time/fake.py` is the test implementation:

- **Default time:** `datetime(2024, 1, 15, 14, 30, 0)` (`DEFAULT_FAKE_TIME`)
- **Sleep tracking:** `sleep_calls` property returns a `list[float]` of all sleep durations passed to `sleep()`, without actually sleeping
- **Configurable:** Constructor accepts optional `current_time` and `monotonic_values` parameters

### Usage in Tests

<!-- Source: packages/erk-shared/src/erk_shared/gateway/time/fake.py, FakeTime -->

`context_for_test()` creates an `ErkContext` with `FakeTime()` by default. Tests that need a specific time can pass a custom `FakeTime` with a `current_time` parameter. See `FakeTime` in `packages/erk-shared/src/erk_shared/gateway/time/fake.py` for the constructor interface.

## Production Integration

In production code, `ctx.time` is a `RealTime` instance that delegates to the standard library. The `ErkContext.time` field is set during context creation.

## Function Signatures

Functions that need the current time should accept a `now: datetime` parameter instead of calling `datetime.now()` internally. The caller passes `ctx.time.now()`.

### Example: Worktree Naming

<!-- Source: packages/erk-shared/src/erk_shared/naming.py, ensure_unique_worktree_name_with_date() -->

`ensure_unique_worktree_name_with_date()` at `packages/erk-shared/src/erk_shared/naming.py` accepts `*, now: datetime` and generates a datetime suffix using `now.strftime()`. Callers pass `ctx.time.now()` for testability. The docstring states: "Callers should pass ctx.time.now() for testability."

## Anti-Patterns

**WRONG:** Importing `time` or `datetime` for direct time access in production code.

```python
# BAD: Direct time access — untestable, flaky
import time
from datetime import datetime

time.sleep(5)
timestamp = datetime.now()
```

**CORRECT:** Using the time gateway through context.

```python
# GOOD: Gateway access — deterministic in tests
ctx.time.sleep(5)
timestamp = ctx.time.now()
```
