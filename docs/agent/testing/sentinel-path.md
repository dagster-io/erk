---
title: SentinelPath Test Utility
read_when:
  - "extending SentinelPath for new filesystem operations"
  - "testing code that creates/deletes files without real filesystem"
  - "need in-memory filesystem simulation in tests"
---

# SentinelPath Test Utility

`SentinelPath` (`tests/test_utils/paths.py`) provides an in-memory filesystem simulation for testing code that manipulates files without touching the real filesystem.

## When to Use

- Testing file existence checks without real files
- Testing file creation/deletion logic
- Avoiding `tmp_path` overhead for simple file operations
- Tests using `erk_inmem_env()` fixture

## When NOT to Use

Use `tmp_path` fixture instead when:

- Testing code that reads file content from disk
- Testing directory traversal or iteration
- Testing symlink behavior
- Integration tests with real filesystem operations

## Key Pattern: Class-Level Storage

SentinelPath uses a class variable `_file_storage: dict[str, str]` to track "existing" files:

```python
# Class-level storage (shared across all instances)
_file_storage: dict[str, str] = {}
```

Supported operations:

| Method         | Behavior                          |
| -------------- | --------------------------------- |
| `touch()`      | Adds path to storage (empty file) |
| `unlink()`     | Removes from storage              |
| `exists()`     | Checks storage membership         |
| `write_text()` | Stores content in storage         |
| `read_text()`  | Retrieves content from storage    |
| `mkdir()`      | No-op (directories assumed exist) |
| `resolve()`    | Returns self (no-op)              |
| `expanduser()` | Returns self (no-op)              |

Operations that throw errors (enforce fake usage):

| Method      | Why                         |
| ----------- | --------------------------- |
| `is_dir()`  | Use fake operations instead |
| `is_file()` | Use fake operations instead |

## Extending SentinelPath

When adding new filesystem operations:

1. **Modify `_file_storage` appropriately** - Use `str(self)` as key
2. **Match the `pathlib.Path` method signature** - Same parameters and return type
3. **Operate on `str(self)` for storage keys** - Consistent path representation

Example: Adding a new method:

```python
def new_method(self, param: str) -> bool:
    """Description matching Path.new_method behavior."""
    path_str = str(self)
    # Implement using _file_storage
    return path_str in SentinelPath._file_storage
```

## Common Patterns

### Testing marker file operations

```python
def test_marker_lifecycle() -> None:
    worktree = sentinel_path("/test/worktree")
    marker = worktree / ".erk" / "pending-extraction"

    # Create marker
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()
    assert marker.exists()

    # Delete marker
    marker.unlink()
    assert not marker.exists()
```

### Clearing storage between tests

```python
@pytest.fixture(autouse=True)
def clean_sentinel_storage() -> None:
    """Ensure clean slate for each test."""
    SentinelPath.clear_file_storage()
    yield
    SentinelPath.clear_file_storage()
```

## Related Topics

- [Sentinel Path Compatibility](../architecture/sentinel-path-compatibility.md) - Making production code work with sentinel paths
- [Testing Guide](testing.md) - Overall testing patterns
