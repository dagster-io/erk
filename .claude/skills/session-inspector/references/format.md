# Session Log Format Reference

Complete specification for Claude Code session logs stored in `~/.claude/projects/`.

## Directory Structure

### Base Location

```
~/.claude/projects/
```

All session logs are stored under this directory, organized by project path.

### Project Directory Encoding

Project directories use deterministic path encoding:

1. Prepend with `-`
2. Replace `/` with `-`
3. Replace `.` with `-`

**Examples:**

```
/Users/foo/code/myapp
  → ~/.claude/projects/-Users-foo-code-myapp

/Users/foo/.config/app
  → ~/.claude/projects/-Users-foo--config-app
  (Note: double dash for hidden directories)

/Users/foo/.erk/repos/erk/worktrees/feature-branch
  → ~/.claude/projects/-Users-foo--erk-repos-erk-worktrees-feature-branch
```

### File Types

**Main session logs:** `<session-id>.jsonl`

- One file per Claude Code session
- Session ID is the filename (without `.jsonl` extension)
- Contains the main conversation thread

**Agent subprocess logs:** `agent-<agent-id>.jsonl`

- One file per agent subprocess
- Agent types: `devrun`, `Plan`, `Explore`, `gt-update-pr-submitter`, etc.
- Linked to parent session via `sessionId` field

## JSONL Format

Each line is a JSON object representing one conversation entry:

```json
{
  "sessionId": "abc123-def456",
  "type": "user|assistant|tool_result",
  "message": {
    "content": [...],
    "timestamp": 1700000000.0
  },
  "gitBranch": "feature-branch",
  "usage": {...}
}
```

### Key Fields

| Field       | Type   | Description                                               |
| ----------- | ------ | --------------------------------------------------------- |
| `sessionId` | string | UUID identifying the session                              |
| `type`      | string | Entry type: `user`, `assistant`, `tool_result`, `summary` |
| `message`   | object | Message content (structure varies by type)                |
| `timestamp` | float  | Unix timestamp (in message object)                        |
| `gitBranch` | string | Current git branch (optional)                             |
| `usage`     | object | Token usage statistics                                    |
| `slug`      | string | Plan mode identifier (maps to ~/.claude/plans/{slug}.md)  |

## Entry Types

### User Entry

```json
{
  "sessionId": "test-session",
  "type": "user",
  "message": {
    "content": [{ "type": "text", "text": "Run pytest tests" }],
    "timestamp": 1700000000.0
  }
}
```

### Assistant Entry with Tool Use

```json
{
  "sessionId": "test-session",
  "type": "assistant",
  "message": {
    "content": [
      { "type": "text", "text": "I'll run the tests" },
      {
        "type": "tool_use",
        "name": "Bash",
        "id": "toolu_abc123",
        "input": { "command": "pytest", "description": "Run unit tests" }
      }
    ],
    "timestamp": 1700000001.0
  }
}
```

### Tool Result Entry

```json
{
  "sessionId": "test-session",
  "type": "tool_result",
  "message": {
    "tool_use_id": "toolu_abc123",
    "content": [
      { "type": "text", "text": "Exit code 0\n===== 42 passed in 1.23s =====" }
    ],
    "is_error": false,
    "timestamp": 1700000002.0
  }
}
```

### File History Snapshot Entry

```json
{
  "sessionId": "test-session",
  "type": "file-history-snapshot",
  "file-snapshot": {
    "file_path": "/path/to/file.py",
    "content": "...",
    "timestamp": 1700000003.0
  }
}
```

### Plan Mode Entry (with slug)

When Plan Mode is exited, the assistant entry includes a `slug` field:

```json
{
  "sessionId": "abc123",
  "type": "assistant",
  "slug": "my-feature-plan",
  "message": {
    "role": "assistant",
    "content": [
      { "type": "text", "text": "I'll create a plan for this feature." }
    ]
  },
  "cwd": "/projects/myapp",
  "gitBranch": "main"
}
```

**Key characteristics:**

- `slug` appears as top-level field on `type: "assistant"` entries
- Added when Plan Mode is exited (plan approved and saved)
- Plan file location: `~/.claude/plans/{slug}.md`

### Summary Entry (Context Compaction)

When context is compacted, a summary entry is created:

```json
{
  "sessionId": "abc123",
  "type": "summary",
  "message": {
    "content": "Summary of previous conversation...",
    "timestamp": 1700003600.0
  }
}
```

## Session ID

### Format

UUID-like strings (format not strictly enforced):

- Examples: `abc123-def456`, `2024-11-23-session`

### Environment Variable

```bash
SESSION_CONTEXT="session_id=abc123-def456"
```

### Extraction

```python
import os

def get_current_session_id() -> str | None:
    session_context = os.environ.get("SESSION_CONTEXT")
    if not session_context:
        return None
    if "session_id=" in session_context:
        parts = session_context.split("session_id=")
        if len(parts) == 2:
            return parts[1].strip()
    return None
```

## Agent ID

### Format

Hex/alphanumeric identifiers, often 8 characters:

- Examples: `17cfd3f4`, `2a3b4c5d`

### Extraction from Filename

```python
agent_id = log_path.stem.replace("agent-", "")
# agent-17cfd3f4.jsonl → 17cfd3f4
```

## Session Lifecycle

### Session ID Persistence

Session IDs persist across context compactions. When a conversation runs out of context:

1. Earlier parts are summarized
2. Conversation continues with condensed context
3. **Same session ID is kept**

This means:

- A single session log can contain multiple "generations"
- Scratch files at `.erk/scratch/<session-id>/` remain accessible
- Agent subprocesses before/after compaction share the same parent ID

### Compaction Boundary Detection

```python
def find_compaction_boundaries(entries: list[dict]) -> list[int]:
    """Find indices where context compaction occurred."""
    return [
        i for i, entry in enumerate(entries)
        if entry.get("type") == "summary"
    ]
```

## Special Cases

### Hidden Directories

Leading dots become double dashes:

```
/Users/foo/.config → -Users-foo--config
/Users/foo/.erk    → -Users-foo--erk
```

### Backward Compatibility

Older logs may not have `sessionId` field. Code should handle missing fields gracefully:

```python
if entry_session is not None and entry_session != session_id:
    continue  # Only skip if sessionId exists and doesn't match
```

### Empty and Warmup Sessions

Detection logic:

- **Empty:** < 3 entries OR no meaningful user/assistant interaction
- **Warmup:** Contains "warmup" keyword in first user message

### Malformed JSONL

Always wrap JSON parsing in try-except:

```python
try:
    entry = json.loads(line)
except json.JSONDecodeError:
    continue  # Skip malformed lines
```

## Token Usage

### Usage Object Fields

```json
{
  "usage": {
    "input_tokens": 12345,
    "output_tokens": 678,
    "cache_read_input_tokens": 10000,
    "cache_creation_input_tokens": 2000
  }
}
```

### Token Estimation

When actual counts unavailable:

```python
estimated_tokens = len(text) // 4
```

## File Size Correlation

Rough estimates (vary by content):

| File Size | Approximate Messages |
| --------- | -------------------- |
| 10 KB     | ~5-10 messages       |
| 50 KB     | ~25-50 messages      |
| 100 KB    | ~50-100 messages     |
| 500 KB    | ~200-400 messages    |

## Code Examples

### Parse Session Log

```python
import json
from pathlib import Path

def parse_session_log(session_file: Path) -> list[dict]:
    """Parse a JSONL session log file."""
    entries = []
    with open(session_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError:
                continue
    return entries
```

### Find Agent Logs for Session

```python
def find_agent_logs_for_session(
    project_dir: Path,
    session_id: str
) -> list[Path]:
    """Find all agent logs linked to a specific session."""
    agent_logs = []
    for agent_file in project_dir.glob("agent-*.jsonl"):
        try:
            with open(agent_file, encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i >= 10:
                        break
                    try:
                        entry = json.loads(line)
                        if entry.get("sessionId") == session_id:
                            agent_logs.append(agent_file)
                            break
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue
    return agent_logs
```

### Extract Key Messages

```python
def extract_key_messages(entries: list[dict]) -> list[dict]:
    """Extract user and assistant text messages."""
    messages = []
    for entry in entries:
        entry_type = entry.get("type")
        if entry_type in ("tool_result", "summary"):
            continue
        message = entry.get("message", {})
        content = message.get("content", [])
        for item in content:
            if item.get("type") == "text":
                text = item.get("text", "").strip()
                if text:
                    messages.append({
                        "type": entry_type,
                        "text": text,
                        "timestamp": message.get("timestamp")
                    })
    return messages
```
