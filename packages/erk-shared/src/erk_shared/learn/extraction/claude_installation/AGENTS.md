# Claude Code Session Store

Gateway abstraction for Claude Code session data operations.

## Related Documentation

**Before modifying this code, read the session documentation:**

@docs/learned/sessions/

## Architecture

This package follows the gateway pattern with three implementations:

| File      | Purpose                                                      |
| --------- | ------------------------------------------------------------ |
| `abc.py`  | Abstract interface (`ClaudeCodeSessionStore`)                |
| `real.py` | Production implementation reading from `~/.claude/projects/` |
| `fake.py` | In-memory fake for testing (`FakeClaudeCodeSessionStore`)    |

## Key Concepts

### Session Types

- **Main sessions**: `<session-id>.jsonl` - primary conversation thread
- **Agent sessions**: `agent-<agent-id>.jsonl` - subprocess logs with `parent_session_id`

### Project Directory Encoding

Project paths are encoded deterministically:

- `/Users/foo/code/app` → `-Users-foo-code-app`
- Replace `/` with `-`, replace `.` with `-`

See `_get_project_dir()` in `real.py` for the walk-up search algorithm.

## Testing

Use `FakeClaudeCodeSessionStore` with `FakeProject` and `FakeSessionData`:

```python
from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
    FakeProject,
    FakeSessionData,
)

store = FakeClaudeCodeSessionStore(
    projects={
        tmp_path: FakeProject(
            sessions={
                "session-id": FakeSessionData(
                    content='{"type": "user", ...}\n',
                    size_bytes=1024,
                    modified_at=time.time(),
                )
            }
        )
    }
)
```

See `docs/learned/testing/session-store-testing.md` for detailed patterns.
