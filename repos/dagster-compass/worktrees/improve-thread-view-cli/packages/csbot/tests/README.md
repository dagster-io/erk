# Test Organization

This document provides a quick reference for understanding and organizing tests in the csbot project.

## Directory Structure

```
tests/
├── integration/        # Integration tests (external I/O, slower execution)
│   ├── bot_server/
│   ├── context_store_integration_tests/
│   ├── github/
│   ├── storage/postgres/
│   ├── tasks/smoke_tests/
│   ├── temporal/
│   ├── usage_monitoring/
│   └── webapp/
└── ...                 # Unit tests (pure functions, mocked dependencies, fast)
```

## Running Tests

```bash
# Run unit tests only (fast, excludes integration tests)
make test

# Run integration tests only (requires external services)
make test-integration

# Run all tests (unit + integration)
make test-all
```

## Classification Criteria

### Unit Tests (tests/)

Place tests in `tests/` when they:

- Test pure functions with no external I/O
- Use mocked dependencies (Mock, AsyncMock)
- Execute quickly (typically < 0.1s per test)
- Verify algorithmic correctness
- Use property-based testing (Hypothesis)

**Examples:**

- Pure computation and data transformation logic
- Business logic with mocked external dependencies
- Property-based tests (even if slow due to fuzzing)

### Integration Tests (tests/integration/)

Place tests in `tests/integration/` when they:

- Use real external systems (PostgreSQL, Redis, Temporal, etc.)
- Perform file system I/O (git operations, serialization)
- Make web API calls (FastAPI endpoints, external APIs)
- Test end-to-end workflows across multiple components
- Use testcontainers or similar infrastructure

**Examples:**

- Database operations with real PostgreSQL
- Git repository operations (pygit2, commits, serialization)
- Web endpoint tests with test clients
- Multi-component orchestration workflows

## Important Notes

- **Directory-based separation**: Tests are classified by their location, NOT by pytest markers
- **Make targets**: The `make test` command excludes integration tests via `--ignore=tests/integration/`
- **Parallel execution**: Unit tests can safely run in parallel (`pytest -n auto`)
- **Property-based tests**: Hypothesis tests stay in unit tests unless they perform I/O operations

## Organization by Feature

Integration tests are organized by feature/component:

- `bot_server/`: Slack bot server functionality
- `context_store_integration_tests/`: Context store workflows
- `github/`: Git operations and GitHub integration
- `storage/postgres/`: Database integration
- `temporal/`: Temporal workflow orchestration
- `usage_monitoring/`: Usage tracking integration
- `webapp/`: Web API endpoints

When adding new integration tests, place them in the appropriate subdirectory based on the primary feature being tested.

## Core Testing Principles

### No Test-Only State in Production Code

**Never add state to production code solely for testing.** Test instrumentation belongs in test code.

❌ **Bad:** Test counters/callbacks in production

```python
class BackgroundTask:
    def __init__(self):
        self.tick_count = 0  # Test pollution!
```

✅ **Good:** Instrumentation in test helpers

```python
# Production: clean
class BackgroundTask:
    async def execute_tick(self):
        pass

# Test: wrap for instrumentation
def wrap_task_with_tracker(task, tracker):
    original = task.execute_tick
    async def wrapped():
        await original()
        tracker.count += 1
    task.execute_tick = wrapped
```

## Background Task Testing

### Problem: Non-Deterministic Tests

```python
# ❌ Bad: Arbitrary yield count
await fake_time.sleep_and_yield(0, yields=20)  # Why 20? Flaky!
```

### Solution: ExecutionTracker

Test helpers in `tests/tasks/helpers.py` provide deterministic synchronization:

```python
# ✅ Good: Wait for exact execution count
from tests.tasks.helpers import ExecutionTracker, wrap_task_with_tracker, wait_for_execution_count

tracker = ExecutionTracker()
wrap_task_with_tracker(task, tracker)

await task.start()
await wait_for_execution_count(tracker, target=3)  # Deterministic
await task.stop()
assert tracker.count == 3
```

**Benefits:** Zero production changes, deterministic tests, clear intent.

### When to Use

- **ExecutionTracker:** Testing loop behavior, execution counts
- **Observable state:** Check actual outcomes (DB writes, list appends)

### Migration

```python
# Before: await fake_time.sleep_and_yield(0.5, yields=20)
# After:  await wait_for_execution_count(tracker, target=3)
```
