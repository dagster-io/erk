---
title: Marker File Pattern
read_when:
  - "implementing worktree-scoped state"
  - "need simple persistence across sessions"
  - "working with markers module"
---

# Marker File Pattern

Markers are empty files in `.erk/` directories that signal state without storing data.

## Design Principles

- **Existence is the signal** - No content, just presence/absence
- **Worktree-scoped** - Each worktree has independent markers
- **Survives sessions** - Persists until explicitly deleted
- **Atomic** - File creation/deletion is atomic on most filesystems

## When to Use

Markers are ideal for:

- **Blocking operations** - Require `--force` to proceed when marker exists
- **Session persistence** - Track state that survives shell sessions
- **Simple boolean flags** - When you just need yes/no state

Markers are NOT ideal for:

- **Storing data** - Use a config file or database instead
- **Complex state** - Multiple values or structured data
- **Shared state** - State that needs to be consistent across worktrees

## Implementation

See `src/erk/core/markers.py`:

```python
from erk.core.markers import (
    create_marker,
    marker_exists,
    delete_marker,
    PENDING_EXTRACTION_MARKER,
)

# Create marker
create_marker(worktree_path, PENDING_EXTRACTION_MARKER)

# Check marker
if marker_exists(worktree_path, PENDING_EXTRACTION_MARKER):
    # Block operation or require --force

# Delete marker
delete_marker(worktree_path, PENDING_EXTRACTION_MARKER)
```

## Current Markers

| Marker               | Purpose                                           | Created By    | Deleted By                        |
| -------------------- | ------------------------------------------------- | ------------- | --------------------------------- |
| `pending-extraction` | Blocks worktree deletion until insights extracted | `erk pr land` | `/erk:create-raw-extraction-plan` |

## Adding New Markers

1. **Add constant** in `markers.py`:

   ```python
   MY_NEW_MARKER = "my-marker-name"
   ```

2. **Create where appropriate** - Call `create_marker()` when state changes
3. **Check before operations** - Call `marker_exists()` and require `--force` to bypass
4. **Delete when done** - Call `delete_marker()` when state is cleared
5. **Document** - Add entry to the table above

## Testing Markers

Use `SentinelPath` for marker file operations in tests:

```python
from tests.test_utils.paths import sentinel_path

def test_marker_workflow() -> None:
    worktree = sentinel_path("/test/worktree")
    marker_path = worktree / ".erk" / "my-marker"

    # Create
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.touch()
    assert marker_path.exists()

    # Delete
    marker_path.unlink()
    assert not marker_path.exists()
```

## Related Topics

- [Pending Extraction Workflow](../erk/pending-extraction-workflow.md) - Primary marker use case
- [SentinelPath Test Utility](../testing/sentinel-path.md) - Testing marker operations
- [Glossary: pending-extraction marker](../glossary.md#pending-extraction-marker)
