# Dependency Injection Pattern

**Status:** Established
**Category:** Testing, Architecture
**Related:** [Time Abstraction](./time-abstraction.md)

## Problem Statement

Production code often depends on external systems that are difficult to control in tests:

- Current time and date
- Sleep/delay operations
- File system operations
- Network requests
- Database connections
- Configuration sources

Traditional approaches have issues:

- **Mocking frameworks** - Brittle, hard to understand, obscure intent
- **Global state** - Hidden dependencies, testing interference
- **Conditional logic** - `if testing:` branches pollute production code
- **Monkey patching** - Fragile, breaks IDE navigation and type checking

## Solution Overview

**Constructor injection with production defaults** - Accept dependencies as constructor parameters with sensible production defaults.

```python
class MyService:
    def __init__(
        self,
        datetime_now: DatetimeNow = system_datetime_now,
        async_sleep: AsyncSleep = system_async_sleep,
    ):
        self.datetime_now = datetime_now
        self.async_sleep = async_sleep
```

**Key principles:**

1. **Explicit dependencies** - Constructor signature reveals all external dependencies
2. **Production defaults** - Zero boilerplate in production code
3. **Pure DI** - No frameworks, decorators, or magic
4. **Type-safe** - Full IDE support and type checking

## Implementation Guide

### Step 1: Define Abstraction

Use type aliases for simple interfaces:

```python
# In utils/time.py
from collections.abc import Callable
from datetime import datetime

DatetimeNow = Callable[[], datetime]

def system_datetime_now() -> datetime:
    """Production implementation using actual system time."""
    return datetime.now(tz=timezone.utc)
```

For complex interfaces, use ABC:

```python
from abc import ABC, abstractmethod

class DatabaseConnection(ABC):
    @abstractmethod
    def execute(self, query: str) -> list[dict[str, object]]:
        pass

class PostgresConnection(DatabaseConnection):
    def execute(self, query: str) -> list[dict[str, object]]:
        # Production implementation
        ...
```

### Step 2: Inject Dependencies

Accept dependencies in constructor with production defaults:

```python
class UserService:
    def __init__(
        self,
        db: DatabaseConnection = PostgresConnection(),
        datetime_now: DatetimeNow = system_datetime_now,
    ):
        self.db = db
        self.datetime_now = datetime_now

    def create_user(self, name: str) -> User:
        created_at = self.datetime_now()
        self.db.execute(f"INSERT INTO users (name, created_at) VALUES ('{name}', '{created_at}')")
        return User(name=name, created_at=created_at)
```

### Step 3: Use in Production

Production code uses defaults (zero boilerplate):

```python
# Production code - no parameters needed
service = UserService()
user = service.create_user("Alice")
```

### Step 4: Control in Tests

Tests inject fake implementations:

```python
# Test code
def test_create_user():
    fake_db = FakeDatabaseConnection()
    fake_time = lambda: datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    service = UserService(db=fake_db, datetime_now=fake_time)
    user = service.create_user("Alice")

    assert user.created_at == datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    assert fake_db.executed_queries[0].startswith("INSERT INTO users")
```

## Examples

### Example 1: Time-Dependent Service

```python
# Production code (src/csbot/tasks/background_task.py)
from csbot.utils.time import DatetimeNow, AsyncSleep, system_datetime_now, system_async_sleep

class BackgroundTask:
    def __init__(
        self,
        name: str,
        interval_seconds: float,
        datetime_now: DatetimeNow = system_datetime_now,
        async_sleep: AsyncSleep = system_async_sleep,
    ):
        self.name = name
        self.interval_seconds = interval_seconds
        self.datetime_now = datetime_now
        self.async_sleep = async_sleep
        self.last_run = self.datetime_now()

    async def run_forever(self):
        while self.running:
            await self.execute()
            self.last_run = self.datetime_now()
            await self.async_sleep(self.interval_seconds)

# Test code (tests/tasks/test_background_task.py)
import pytest
from csbot.utils.time import FakeTimeProvider

@pytest.fixture
def fake_time():
    return FakeTimeProvider(initial_seconds=1000000)

@pytest.fixture
def task(fake_time):
    return BackgroundTask(
        name="test_task",
        interval_seconds=5.0,
        datetime_now=fake_time.datetime_now,
        async_sleep=fake_time.async_sleep,
    )

async def test_task_runs_periodically(task, fake_time):
    # Start task
    await task.start()

    # Advance time by 15 seconds
    fake_time.advance(15)

    # Task should have executed 3 times (0s, 5s, 10s, 15s)
    assert task.execution_count >= 3
```

### Example 2: Storage with Time

```python
# Production code (src/csbot/slackbot/storage/idle_detector.py)
class IdleDetector:
    def __init__(
        self,
        idle_threshold_seconds: float,
        datetime_now: DatetimeNow = system_datetime_now,
    ):
        self.idle_threshold_seconds = idle_threshold_seconds
        self.datetime_now = datetime_now
        self.last_activity: dict[str, datetime] = {}

    def record_activity(self, user_id: str):
        self.last_activity[user_id] = self.datetime_now()

    def is_idle(self, user_id: str) -> bool:
        if user_id not in self.last_activity:
            return True

        elapsed = (self.datetime_now() - self.last_activity[user_id]).total_seconds()
        return elapsed >= self.idle_threshold_seconds

# Test code
def test_idle_detection():
    fake_time = FakeTimeProvider(initial_seconds=1000)
    detector = IdleDetector(
        idle_threshold_seconds=300,  # 5 minutes
        datetime_now=fake_time.datetime_now,
    )

    detector.record_activity("user1")
    assert not detector.is_idle("user1")

    fake_time.advance(400)  # Advance 6+ minutes
    assert detector.is_idle("user1")
```

## Common Pitfalls

### ❌ Pitfall 1: Creating Instances as Defaults

```python
# WRONG: Creates single shared instance
class Service:
    def __init__(self, db: Database = PostgresDatabase()):
        self.db = db
```

**Problem:** Default parameter evaluated once at function definition time, creating a shared instance.

**Solution:** Use factory function or check for None:

```python
# CORRECT: Factory function
class Service:
    def __init__(self, db: Database | None = None):
        self.db = db if db is not None else PostgresDatabase()
```

### ❌ Pitfall 2: Mixing Abstraction Styles

```python
# WRONG: Mixing Protocol and ABC
from typing import Protocol
from abc import ABC

class TimeProvider(Protocol):  # Using Protocol
    def now(self) -> datetime: ...

class Storage(ABC):  # Using ABC
    @abstractmethod
    def save(self, data: str): ...
```

**Problem:** Inconsistent abstraction styles confuse developers.

**Solution:** Use ABC consistently (per dignified-python standards):

```python
# CORRECT: Consistent ABC usage
from abc import ABC, abstractmethod

class TimeProvider(ABC):
    @abstractmethod
    def now(self) -> datetime: ...

class Storage(ABC):
    @abstractmethod
    def save(self, data: str): ...
```

### ❌ Pitfall 3: Over-Injecting

```python
# WRONG: Injecting too many dependencies
class Service:
    def __init__(
        self,
        logger: Logger = system_logger,
        metrics: Metrics = system_metrics,
        tracer: Tracer = system_tracer,
        config: Config = system_config,
        db: Database = system_db,
        cache: Cache = system_cache,
        # ... 10 more dependencies
    ):
        ...
```

**Problem:** Constructor becomes unwieldy, suggesting poor cohesion.

**Solution:** Group related dependencies or split the class:

```python
# CORRECT: Group related dependencies
@dataclass(frozen=True)
class ObservabilityDeps:
    logger: Logger
    metrics: Metrics
    tracer: Tracer

system_observability = ObservabilityDeps(
    logger=system_logger,
    metrics=system_metrics,
    tracer=system_tracer,
)

class Service:
    def __init__(
        self,
        db: Database = system_db,
        observability: ObservabilityDeps = system_observability,
    ):
        self.db = db
        self.observability = observability
```

### ❌ Pitfall 4: Testing Production Defaults

```python
# WRONG: Tests rely on production defaults
def test_service():
    service = Service()  # Uses production database!
    service.create_user("test")
```

**Problem:** Tests hit real external systems, causing flakiness and slowness.

**Solution:** Always inject test doubles:

```python
# CORRECT: Explicit test doubles
def test_service():
    fake_db = FakeDatabaseConnection()
    service = Service(db=fake_db)
    service.create_user("test")
    assert fake_db.users == ["test"]
```

## Design Checklist

When adding dependency injection:

- [ ] Constructor parameters have production defaults
- [ ] Abstractions use ABC, not Protocol (per dignified-python)
- [ ] Type aliases used for simple function types
- [ ] No mutable default arguments
- [ ] Production code has zero boilerplate
- [ ] Tests inject explicit test doubles
- [ ] Dependencies are explicit, not hidden

## Related Patterns

- **[Time Abstraction](./time-abstraction.md)** - Specialized DI pattern for time providers
- **Dignified Python** - See [CLAUDE.md](../../CLAUDE.md) for broader coding standards

## References

- [csbot/utils/time.py](../../packages/csbot/src/csbot/utils/time.py) - Time abstraction implementation
- [csbot/slackbot/storage/idle_detector.py](../../packages/csbot/src/csbot/slackbot/storage/idle_detector.py) - Example usage
- [tests/test_idle_detector.py](../../packages/csbot/tests/test_idle_detector.py) - Example tests
