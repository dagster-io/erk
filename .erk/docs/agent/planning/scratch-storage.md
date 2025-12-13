---
title: Scratch Storage
read_when:
  - "writing temp files for AI workflows"
  - "passing files between processes"
  - "understanding scratch directory location"
tripwires:
  - action: "writing to /tmp/"
    warning: "AI workflow files belong in .erk/scratch/<session-id>/, NOT /tmp/."
  - action: "creating temp files for AI workflows"
    warning: "Use worktree-scoped scratch storage for session-specific data."
---

# Scratch Storage

Erk provides a worktree-local scratch directory for inter-process file passing during AI workflows.

## Location

```
{repo_root}/.erk/scratch/sessions/<session-id>/
```

Each Claude session gets its own subdirectory under `sessions/`, making debugging and auditing easier.

### Directory Structure

```
.erk/scratch/
  ├── sessions/<session-id>/     # Session-scoped files (isolated per Claude session)
  │   ├── pr-diff-abc123.diff
  │   ├── haiku-input-xyz.xml
  │   └── ...
  └── <worktree-scoped files>    # Top-level for worktree-scoped scratch files
```

## When to Use Scratch vs /tmp

| Storage                               | Use For                               | Examples                             |
| ------------------------------------- | ------------------------------------- | ------------------------------------ |
| `.erk/scratch/sessions/<session-id>/` | AI workflow intermediate files        | PR diffs, PR bodies, commit messages |
| `/tmp/erk-*`                          | Shell scripts sourced by parent shell | Shell integration, recovery scripts  |
| `/tmp/erk-debug.log`                  | Global diagnostics                    | Debug logging                        |

**Key distinction**: Scratch is scoped to worktree + session. /tmp is for files that must work from any directory.

## API

```python
from erk_shared.scratch.scratch import get_scratch_dir, write_scratch_file

# Get session directory
scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)

# Write file with unique name
file_path = write_scratch_file(
    content="...",
    session_id=session_id,
    suffix=".diff",
    prefix="pr-diff-",
)
```

## Session ID

Session IDs are passed explicitly to CLI commands via `--session-id` options. The agent extracts the session ID from hook reminders (e.g., `📌 session: <id>`) and passes it to CLI commands.

## Path Construction

When preflight writes a file, finalize should use the **same directory**:

```python
# Extract directory from existing scratch file
scratch_dir = diff_file.parent
pr_body = scratch_dir / "pr-body.txt"
```

## Common Mistake

```python
# WRONG: AI workflow files in global /tmp
Path("/tmp/pr-body-1927.txt")

# RIGHT: AI workflow files in worktree scratch (sessions/<session-id>/)
scratch_dir / "pr-body.txt"
```
