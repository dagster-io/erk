# Time Abstraction Pattern

**Status:** Established
**Category:** Testing, Time Management
**Related:** [Dependency Injection](./dependency-injection.md)

## Problem Statement

Time-dependent code is notoriously difficult to test:

- **Slow tests** - `asyncio.sleep()` adds 24-31 seconds to test suite
- **Flaky tests** - Race conditions from real timing
- **Non-deterministic** - Tests pass/fail based on system load
- **Hard to debug** - Timing issues difficult to reproduce

Common problematic patterns:

```python
# ❌ Problems in production code
await asyncio.sleep(5.0)  # Tests must wait 5 real seconds
current_time = datetime.now()  # Tests can't control time
elapsed = time.time() - start_time  # Time advances during test

# ❌ Problems in tests
await asyncio.sleep(0.1)  # "Wait for operation to complete"
await asyncio.sleep(0.01)  # "Let the event loop run"
```

## Solution Overview

**Inject time providers as dependencies** to give tests deterministic control over time advancement without sleeping.

```python
# Production code
class MyService:
    def __init__(
        self,
        async_sleep: AsyncSleep = system_async_sleep,
        datetime_now: DatetimeNow = system_datetime_now,
    ):
        self.async_sleep = async_sleep
        self.datetime_now = datetime_now

    async def periodic_task(self):
        while self.running:
            await self.do_work()
            await self.async_sleep(5.0)  # Injected sleep

# Test code
fake_time = FakeTimeProvider(initial_seconds=1000)
service = MyService(
    async_sleep=fake_time.async_sleep,
    datetime_now=fake_time.datetime_now,
)

await service.start()
fake_time.advance(15)  # Instantly advance 15 seconds
assert service.work_count >= 3  # Should have run 3 times
```

**Benefits:**

- **Instant tests** - No real sleeping, tests complete immediately
- **Deterministic** - Time advances explicitly, no race conditions
- **Debuggable** - Can step through time advancement
- **Coordinated** - All time providers see same time

## Implementation Guide

### Step 1: Understand Existing Time Utilities

The time abstraction is already established in `csbot/utils/time.py`:

```python
# packages/csbot/src/csbot/utils/time.py
from collections.abc import Awaitable, Callable
from datetime import datetime

# Type aliases for function signatures
DatetimeNow = Callable[[], datetime]
SecondsNow = Callable[[], float]
AsyncSleep = Callable[[float], Awaitable[None]]

# Production implementations
def system_datetime_now() -> datetime:
    return datetime.now(tz=timezone.utc)

def system_seconds_now() -> float:
    return time.time()

async def system_async_sleep(duration: float):
    await asyncio.sleep(duration)

# Test implementations
class FakeTimeProvider:
    """Coordinated fake time for deterministic testing."""

    def __init__(self, initial_seconds: float = 0):
        self.current_seconds = initial_seconds

    def datetime_now(self) -> datetime:
        return datetime.fromtimestamp(self.current_seconds, tz=timezone.utc)

    def seconds_now(self) -> float:
        return self.current_seconds

    async def async_sleep(self, duration: float):
        # Instantly advance time instead of sleeping
        self.current_seconds += duration

    def advance(self, seconds: float):
        """Manually advance time for test control."""
        self.current_seconds += seconds
```

### Step 2: Add Time Injection to Production Code

Inject time providers with production defaults:

```python
# Before (no injection)
class BackgroundTask:
    def __init__(self, name: str, interval: float):
        self.name = name
        self.interval = interval

    async def run_forever(self):
        while self.running:
            await self.execute()
            await asyncio.sleep(self.interval)  # ❌ Hard-coded

# After (with injection)
from csbot.utils.time import AsyncSleep, system_async_sleep

class BackgroundTask:
    def __init__(
        self,
        name: str,
        interval: float,
        async_sleep: AsyncSleep = system_async_sleep,  # ✅ Injected
    ):
        self.name = name
        self.interval = interval
        self.async_sleep = async_sleep

    async def run_forever(self):
        while self.running:
            await self.execute()
            await self.async_sleep(self.interval)  # ✅ Uses injected sleep
```

### Step 3: Update Tests to Use Fake Time

Replace real sleeps with fake time advancement:

```python
# Before (slow, flaky)
async def test_background_task():
    task = BackgroundTask(name="test", interval=0.1)
    await task.start()
    await asyncio.sleep(0.3)  # ❌ Real sleep, 300ms wait
    assert task.execution_count >= 3

# After (instant, deterministic)
import pytest
from csbot.utils.time import FakeTimeProvider

@pytest.fixture
def fake_time():
    return FakeTimeProvider(initial_seconds=1000000)

@pytest.fixture
def task(fake_time):
    return BackgroundTask(
        name="test",
        interval=5.0,
        async_sleep=fake_time.async_sleep,
    )

async def test_background_task(task, fake_time):
    await task.start()
    fake_time.advance(15)  # ✅ Instant, advances 15 seconds
    assert task.execution_count >= 3
```

### Step 4: Coordinate Multiple Time Providers

When code uses both `datetime_now` and `async_sleep`, share the same `FakeTimeProvider`:

```python
class Service:
    def __init__(
        self,
        datetime_now: DatetimeNow = system_datetime_now,
        async_sleep: AsyncSleep = system_async_sleep,
    ):
        self.datetime_now = datetime_now
        self.async_sleep = async_sleep
        self.last_update = self.datetime_now()

    async def periodic_update(self):
        while self.running:
            self.last_update = self.datetime_now()  # Record time
            await self.async_sleep(60)  # Wait 60 seconds

# Test with coordinated fake time
@pytest.fixture
def fake_time():
    return FakeTimeProvider(initial_seconds=1000000)

@pytest.fixture
def service(fake_time):
    return Service(
        datetime_now=fake_time.datetime_now,  # Share fake time
        async_sleep=fake_time.async_sleep,     # Share fake time
    )

async def test_service(service, fake_time):
    await service.start()

    initial_time = service.last_update
    fake_time.advance(120)  # Advance 2 minutes

    # Both datetime_now and async_sleep advanced together
    assert (service.last_update - initial_time).total_seconds() >= 120
```

## Examples

### Example 1: Background Task System

**Production code (packages/csbot/src/csbot/tasks/background_task.py):**

```python
from csbot.utils.time import AsyncSleep, DatetimeNow, system_async_sleep, system_datetime_now

class BackgroundTask:
    def __init__(
        self,
        name: str,
        interval_seconds: float,
        async_sleep: AsyncSleep = system_async_sleep,
        datetime_now: DatetimeNow = system_datetime_now,
    ):
        self.name = name
        self.interval_seconds = interval_seconds
        self.async_sleep = async_sleep
        self.datetime_now = datetime_now
        self.execution_count = 0
        self.running = False

    async def start(self):
        self.running = True
        await self._run_loop()

    async def _run_loop(self):
        while self.running:
            await self.execute()
            self.execution_count += 1
            await self.async_sleep(self.interval_seconds)

    async def execute(self):
        # Subclass implements work
        pass
```

**Test code (packages/csbot/tests/tasks/test_background_task.py):**

```python
import pytest
from csbot.tasks.background_task import BackgroundTask
from csbot.utils.time import FakeTimeProvider

@pytest.fixture
def fake_time():
    return FakeTimeProvider(initial_seconds=1000000)

@pytest.fixture
def task(fake_time):
    return BackgroundTask(
        name="test_task",
        interval_seconds=5.0,
        async_sleep=fake_time.async_sleep,
        datetime_now=fake_time.datetime_now,
    )

async def test_periodic_execution(task, fake_time):
    """Task executes periodically at the specified interval."""
    await task.start()

    # Initially executed once
    assert task.execution_count == 1

    # Advance 15 seconds - should trigger 3 more executions
    fake_time.advance(15)
    assert task.execution_count >= 4  # 1 initial + 3 periodic

    # Advance 5 more seconds - 1 more execution
    fake_time.advance(5)
    assert task.execution_count >= 5
```

**Time saved:** 15+ seconds per test file (4 sleeps eliminated)

### Example 2: Rate Limiting / Throttling

**Production code (packages/csbot/src/csbot/slackbot/slack_stream.py):**

```python
from csbot.utils.time import AsyncSleep, system_async_sleep

class SlackStream:
    def __init__(
        self,
        min_chunk_interval: float = 0.05,
        async_sleep: AsyncSleep = system_async_sleep,
    ):
        self.min_chunk_interval = min_chunk_interval
        self.async_sleep = async_sleep
        self.last_chunk_time = 0.0

    async def send_chunk(self, chunk: str):
        # Rate limit: ensure minimum interval between chunks
        await self.async_sleep(self.min_chunk_interval)
        self.last_chunk_time = time.time()
        await self._send_to_slack(chunk)
```

**Test code (packages/csbot/tests/test_slackbot_slackstream.py):**

```python
@pytest.fixture
def fake_time():
    return FakeTimeProvider(initial_seconds=1000000)

@pytest.fixture
def stream(fake_time):
    return SlackStream(
        min_chunk_interval=0.05,
        async_sleep=fake_time.async_sleep,
    )

async def test_rate_limiting(stream, fake_time):
    """Stream enforces minimum interval between chunks."""
    for i in range(10):
        await stream.send_chunk(f"chunk{i}")

    # All chunks sent instantly in test (no 0.5s wait)
    assert stream.chunks_sent == 10
```

**Time saved:** 2-3 seconds per test file (10 sleeps eliminated)

### Example 3: Expiry and TTL

**Production code (packages/csbot/src/csbot/slackbot/storage/storage.py):**

```python
from csbot.utils.time import SecondsNow, system_seconds_now

class Storage:
    def __init__(
        self,
        ttl_seconds: float,
        seconds_now: SecondsNow = system_seconds_now,
    ):
        self.ttl_seconds = ttl_seconds
        self.seconds_now = seconds_now
        self.cache: dict[str, tuple[object, float]] = {}

    def set(self, key: str, value: object):
        expiry = self.seconds_now() + self.ttl_seconds
        self.cache[key] = (value, expiry)

    def get(self, key: str) -> object | None:
        if key not in self.cache:
            return None

        value, expiry = self.cache[key]
        if self.seconds_now() >= expiry:
            del self.cache[key]  # Expired
            return None

        return value
```

**Test code (packages/csbot/tests/storage/test_storage_expiry.py):**

```python
def test_expiry():
    fake_time = FakeTimeProvider(initial_seconds=1000)
    storage = Storage(ttl_seconds=60, seconds_now=fake_time.seconds_now)

    storage.set("key1", "value1")
    assert storage.get("key1") == "value1"

    fake_time.advance(59)  # Just before expiry
    assert storage.get("key1") == "value1"

    fake_time.advance(2)  # Past expiry
    assert storage.get("key1") is None
```

**Time saved:** 2+ seconds per test file (3 sleeps eliminated)

## Common Pitfalls

### ❌ Pitfall 1: Mixing Real and Fake Time

```python
# WRONG: Mixing real and fake time
fake_time = FakeTimeProvider()
service = MyService(
    async_sleep=fake_time.async_sleep,  # Fake
    datetime_now=system_datetime_now,   # Real - INCONSISTENT!
)

fake_time.advance(60)
# datetime_now() hasn't advanced - time drift!
```

**Solution:** Always use the same `FakeTimeProvider` for all time operations:

```python
# CORRECT: Coordinated fake time
fake_time = FakeTimeProvider()
service = MyService(
    async_sleep=fake_time.async_sleep,
    datetime_now=fake_time.datetime_now,  # Same provider
)
```

### ❌ Pitfall 2: Advancing Time After Await

```python
# WRONG: Time advancement happens during await
async def test_wrong():
    fake_time = FakeTimeProvider()
    task = BackgroundTask(async_sleep=fake_time.async_sleep, interval=5.0)

    await task.start()  # ❌ async_sleep() advances time implicitly

    fake_time.advance(10)  # Additional advancement
    # Total time advanced is unclear!
```

**Solution:** Be aware that `fake_time.async_sleep()` advances time:

```python
# CORRECT: Understand implicit advancement
async def test_correct():
    fake_time = FakeTimeProvider()
    task = BackgroundTask(async_sleep=fake_time.async_sleep, interval=5.0)

    await task.start()  # Sleeps 5 seconds (fake_time += 5)

    # To reach 15 seconds total, advance 10 more
    fake_time.advance(10)
    assert fake_time.current_seconds >= 15
```

### ❌ Pitfall 3: Keeping Sleep in Timeout Tests

```python
# WRONG: Replacing sleep in timeout testing
async def test_timeout_with_fake_time():
    fake_time = FakeTimeProvider()

    with pytest.raises(asyncio.TimeoutError):
        async with asyncio.timeout(1.0):
            await fake_time.async_sleep(2.0)  # ❌ Instant, timeout won't trigger!
```

**Solution:** Keep real sleep when testing actual timeout behavior:

```python
# CORRECT: Use real sleep for timeout tests
async def test_timeout():
    with pytest.raises(asyncio.TimeoutError):
        async with asyncio.timeout(0.01):
            await asyncio.sleep(10)  # ✅ Real sleep, timeout will trigger
```

Document intentional sleeps:

```python
# INTENTIONAL: Testing actual timeout mechanism
await asyncio.sleep(100)  # Will be interrupted by timeout
```

### ❌ Pitfall 4: Not Propagating Injection

```python
# WRONG: Accepting injection but not passing it down
class Manager:
    def __init__(self, async_sleep: AsyncSleep = system_async_sleep):
        self.async_sleep = async_sleep
        self.worker = Worker()  # ❌ Worker uses real sleep!

class Worker:
    def __init__(self):
        pass

    async def work(self):
        await asyncio.sleep(5.0)  # ❌ Hard-coded real sleep
```

**Solution:** Propagate injected dependencies to all components:

```python
# CORRECT: Pass injection through the hierarchy
class Manager:
    def __init__(self, async_sleep: AsyncSleep = system_async_sleep):
        self.async_sleep = async_sleep
        self.worker = Worker(async_sleep=async_sleep)  # ✅ Propagate

class Worker:
    def __init__(self, async_sleep: AsyncSleep = system_async_sleep):
        self.async_sleep = async_sleep

    async def work(self):
        await self.async_sleep(5.0)  # ✅ Uses injected sleep
```

## When to Keep Real Sleeps

Keep `asyncio.sleep()` when:

1. **Testing timeout mechanisms** - Need real time for timeouts to trigger
2. **Testing external service health** - Polling for service readiness
3. **Duration is minimal** - <0.01s may not be worth the complexity

Document intentional sleeps with clear comments:

```python
# INTENTIONAL: Testing actual timeout behavior
async with asyncio.timeout(0.01):
    await asyncio.sleep(10)  # Will be interrupted

# INTENTIONAL: Polling for service health
while not service.is_ready():
    await asyncio.sleep(0.01)
```

## Decision Tree

```
Does your code use time-related operations?
├─ Yes: Uses datetime.now(), time.time(), or asyncio.sleep()
│   ├─ Is it in production code?
│   │   ├─ Yes → Add time injection with production defaults
│   │   └─ No → Continue
│   └─ Is it in test code?
│       ├─ Testing timeout behavior? → Keep real sleep, document as INTENTIONAL
│       ├─ Polling external service? → Keep real sleep, document as INTENTIONAL
│       ├─ Duration < 0.01s? → Consider keeping (low value)
│       └─ Otherwise → Use FakeTimeProvider
└─ No → No changes needed
```

## Migration Checklist

When adding time abstraction to existing code:

- [ ] Identify all time operations (`datetime.now()`, `time.time()`, `asyncio.sleep()`)
- [ ] Add time injection to production code with defaults
- [ ] Create `FakeTimeProvider` fixture in tests
- [ ] Replace test sleeps with `fake_time.advance()`
- [ ] Verify time providers are coordinated (same `FakeTimeProvider` instance)
- [ ] Document intentional sleeps with `# INTENTIONAL:` comments
- [ ] Measure test time before and after
- [ ] Run tests to verify deterministic behavior

## Success Metrics

After applying time abstraction:

- **Test speed** - Time saved from eliminated sleeps
- **Determinism** - No timing-based test failures
- **Clarity** - Explicit time advancement in tests
- **Debuggability** - Can step through time operations

## Related Patterns

- **[Dependency Injection](./dependency-injection.md)** - General DI pattern that time abstraction follows
- **Background Task System** - Primary consumer of time abstraction
- **Rate Limiting** - Uses time injection for throttling tests

## References

- **Implementation:** [packages/csbot/src/csbot/utils/time.py](../../packages/csbot/src/csbot/utils/time.py)
- **Examples:**
  - [packages/csbot/src/csbot/tasks/background_task.py](../../packages/csbot/src/csbot/tasks/background_task.py)
  - [packages/csbot/src/csbot/slackbot/storage/idle_detector.py](../../packages/csbot/src/csbot/slackbot/storage/idle_detector.py)
- **Tests:**
  - [packages/csbot/tests/tasks/test_background_task.py](../../packages/csbot/tests/tasks/test_background_task.py)
  - [packages/csbot/tests/test_idle_detector.py](../../packages/csbot/tests/test_idle_detector.py)
  - [packages/csbot/tests/storage/test_storage_expiry.py](../../packages/csbot/tests/storage/test_storage_expiry.py)
