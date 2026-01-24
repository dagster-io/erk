---
title: Integration Testing Patterns
read_when:
  - "writing integration tests that interact with filesystem"
  - "testing time-dependent operations"
  - "handling mtime resolution in tests"
---

# Integration Testing Patterns

Patterns for writing reliable integration tests that interact with real system resources.

## Filesystem Mtime Resolution

Different filesystems have different mtime (modification time) precision:

| Filesystem | Resolution |
| ---------- | ---------- |
| ext4       | Nanosecond |
| HFS+       | 1 second   |
| APFS       | Nanosecond |
| FAT32      | 2 seconds  |

### Problem: Mtime-Based Tests Flake

When testing mtime-based cache invalidation, operations that complete within the filesystem's resolution may appear unchanged:

```python
# FLAKY: May pass or fail depending on execution speed
def test_cache_invalidation():
    write_file("data.json", {"v": 1})
    result1 = cache.read()  # Caches based on mtime

    write_file("data.json", {"v": 2})  # Same mtime if fast!
    result2 = cache.read()  # May return stale data

    assert result2["v"] == 2  # FLAKY
```

### Solution: Sleep Between Writes

Add minimal sleeps to ensure mtime changes:

```python
import time

def test_cache_invalidation():
    write_file("data.json", {"v": 1})
    result1 = cache.read()

    time.sleep(0.01)  # 10ms - enough for any filesystem
    write_file("data.json", {"v": 2})
    result2 = cache.read()

    assert result2["v"] == 2  # Reliable
```

### Guidelines

| Test Type         | Sleep Duration | Notes                             |
| ----------------- | -------------- | --------------------------------- |
| Unit tests        | Avoid sleeps   | Use mocks or dependency injection |
| Integration tests | 10-50ms        | Enough for mtime resolution       |
| CI performance    | Minimize count | Batch related operations          |

## Time Dependency Injection

For faster tests, inject time dependencies instead of sleeping:

```python
from erk_shared.time import Time, FakeTime

class Cache:
    def __init__(self, time: Time) -> None:
        self._time = time
        self._cached_mtime: float | None = None

    def is_stale(self, file_mtime: float) -> bool:
        return self._cached_mtime != file_mtime
```

In tests:

```python
def test_cache_staleness():
    fake_time = FakeTime()
    cache = Cache(time=fake_time)

    # No actual sleeping needed - control time directly
    cache._cached_mtime = 1000.0
    assert cache.is_stale(1001.0)  # Different mtime = stale
```

## Subprocess Output in Integration Tests

When testing commands that invoke subprocesses, capture output reliably:

```python
def test_command_output(tmp_path):
    result = subprocess.run(
        ["erk", "some-command"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,  # Prevent hangs
    )

    assert result.returncode == 0
    assert "expected output" in result.stdout
```

### Timeout Guidelines

| Operation          | Suggested Timeout |
| ------------------ | ----------------- |
| Simple CLI command | 10s               |
| Network operation  | 30s               |
| Build/compile      | 120s              |

## Parallel Test Safety

When tests share filesystem state, isolate properly:

```python
def test_with_isolation(tmp_path, monkeypatch):
    # Isolate from user's home directory
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    # Now ~/.config won't conflict with user's real config
    ...
```

See [Exec Script Testing Patterns](exec-script-testing.md) for more isolation patterns.

## Related Topics

- [Exec Script Testing Patterns](exec-script-testing.md) - Testing exec commands
- [Integration Test Speed](integration-test-speed.md) - Performance optimization
- [Erk Architecture Patterns](../architecture/erk-architecture.md) - Time dependency injection
