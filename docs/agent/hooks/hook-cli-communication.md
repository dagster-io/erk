---
title: Hook-to-CLI Data Flow
read_when:
  - "passing data from hooks to CLI commands"
  - "hooks need to share state with other processes"
  - "understanding hook process isolation"
tripwires:
  - action: "trying to set environment variables in hooks for CLI tools"
    warning: "Hooks run as isolated subprocesses. Use file-based persistence instead."
---

# Hook-to-CLI Data Flow

## The Constraint

Claude Code hooks run as **isolated subprocesses**. They cannot:

- Set environment variables for other processes
- Modify the parent shell's state
- Pass data to CLI commands via process inheritance

Hooks can ONLY:

- Output text to stdout (which appears in LLM context)
- Write files to the filesystem
- Exit with a status code

## The Pattern: File-Based Persistence

When a hook needs to share data with CLI commands, use worktree-scoped file storage:

### Hook writes data:

```python
# In hook code
session_file = Path(".erk/scratch/current-session-id")
session_file.parent.mkdir(parents=True, exist_ok=True)
session_file.write_text(session_id, encoding="utf-8")

# Still output for LLM context
click.echo(f"SESSION_CONTEXT: session_id={session_id}")
```

### CLI reads data:

```python
from functools import cache

@cache
def _session_id_file_path() -> Path:
    return Path(".erk/scratch/current-session-id")

def get_session_id() -> str | None:
    session_file = _session_id_file_path()
    if session_file.exists():
        return session_file.read_text(encoding="utf-8").strip()
    return None
```

## Why Worktree-Scoped?

The file lives at `.erk/scratch/` (relative to worktree root) because:

1. **Isolation**: Each worktree can have different session state
2. **Cleanup**: State is automatically scoped to worktree lifecycle
3. **Parallel safety**: Multiple worktrees don't conflict

## Edge Cases

1. **Stale data**: If user starts new session without hook firing, old file remains
   - CLI should validate data freshness when critical

2. **Parallel sessions**: Multiple sessions in same worktree overwrite the file
   - Acceptable for "current session" use case
   - Use session-scoped paths for session-specific data: `.erk/scratch/sessions/<session-id>/`
