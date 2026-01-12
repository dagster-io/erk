---
title: Session Hierarchy
read_when:
  - "understanding Claude Code session structure"
  - "working with parent and agent sessions"
  - "finding session files on disk"
  - "correlating agent logs to parent sessions"
  - "implementing session-scoped file discovery"
---

# Session Hierarchy

Claude Code sessions have a parent-child hierarchy where main sessions spawn agent sessions for delegated tasks.

## Conceptual Model

```
┌─────────────────────────────────────────────────────────┐
│                      Parent Session                     │
│  (main conversation with user)                          │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Agent       │  │ Agent       │  │ Agent       │     │
│  │ (devrun)    │  │ (Explore)   │  │ (Plan)      │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

- **Parent session**: The main conversation thread with the user
- **Agent session**: A subprocess spawned via the `Task` tool to handle specific work

Agents are autonomous subprocesses that:

- Run independently with their own context
- Report results back to the parent
- Have their own conversation logs

## Physical Layout on Disk

Sessions are stored in `~/.claude/projects/<encoded-path>/`:

```
~/.claude/projects/-Users-foo-myproject/
├── abc12345-1234-5678-9abc-def012345678.jsonl   # Parent session
├── xyz98765-4321-8765-dcba-210987654321.jsonl   # Another parent session
├── agent-a65aee7.jsonl                          # Agent session
├── agent-a3ea803.jsonl                          # Agent session
└── agent-b12cd34.jsonl                          # Agent session
```

### Path Encoding

Project paths are encoded by replacing `/` and `.` with `-`:

- `/Users/foo/my.project` → `-Users-foo-my-project`

### File Naming

| Pattern                  | Type           | Example                                      |
| ------------------------ | -------------- | -------------------------------------------- |
| `<uuid>.jsonl`           | Parent session | `abc12345-1234-5678-9abc-def012345678.jsonl` |
| `agent-<short-id>.jsonl` | Agent session  | `agent-a65aee7.jsonl`                        |

## Identifying Session Types

### By filename

```python
is_agent = filename.startswith("agent-")
```

### By content (first entry)

Agent sessions have `agentId` and `sessionId` (parent link) in their entries:

```json
{
  "type": "user",
  "sessionId": "abc12345-1234-5678-9abc-def012345678",
  "agentId": "a65aee7",
  ...
}
```

Parent sessions have only `sessionId` (their own ID):

```json
{
  "type": "user",
  "sessionId": "abc12345-1234-5678-9abc-def012345678",
  ...
}
```

## Linking Parent to Agent

### Finding an agent's parent

In the agent log, read `sessionId` from any entry:

```python
def get_parent_session_id(agent_log_path: Path) -> str | None:
    content = agent_log_path.read_text()
    for line in content.split("\n")[:10]:
        if not line.strip().startswith("{"):
            continue
        entry = json.loads(line)
        if "sessionId" in entry:
            return entry["sessionId"]
    return None
```

### Finding a parent's agents

Option 1: Scan all `agent-*.jsonl` files and check their `sessionId`

Option 2: Parse parent session for `toolUseResult.agentId` values (more efficient)

## Key Fields Reference

### Parent session entry

```json
{
  "sessionId": "abc12345-...",      // This session's ID
  "type": "assistant",
  "message": {...},
  "timestamp": "2025-12-22T18:27:06.007Z"
}
```

### Agent session entry

```json
{
  "sessionId": "abc12345-...",      // PARENT session's ID
  "agentId": "a65aee7",             // This agent's short ID
  "type": "user",
  "message": {...},
  "timestamp": "2025-12-22T18:27:06.119Z"
}
```

### Task invocation result (in parent)

```json
{
  "type": "user",
  "message": {
    "content": [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_01Mzn..."
      }
    ]
  },
  "toolUseResult": {
    "agentId": "a65aee7", // Links to agent-a65aee7.jsonl
    "status": "completed"
  }
}
```

## Implementing Session-Scoped File Discovery

When writing functions that discover files belonging to a specific session (agent logs, planning logs, etc.), you MUST filter by session ID.

### The Pattern

```python
def discover_files_for_session(directory: Path, session_id: str) -> list[Path]:
    """Find files belonging to a specific session."""
    matching = []
    for path in directory.glob("agent-*.jsonl"):
        # Read first entry to check session ownership
        content = path.read_text()
        first_line = content.split("\n", 1)[0]
        if not first_line.strip():
            continue
        entry = json.loads(first_line)
        if entry.get("sessionId") == session_id:
            matching.append(path)
    return matching
```

### Why This Matters

A project directory may contain thousands of agent logs from many sessions. Without session ID filtering:

- A 67KB session file could load 190MB of unrelated agent logs
- Processing time increases dramatically
- Memory usage explodes

### Reference Implementation

See `preprocess_session.py`:

- `discover_agent_logs()` - Discovers agent logs for a session
- `discover_planning_agent_logs()` - Discovers planning agent logs for a session

Both follow this pattern: glob for candidate files, read first entry, check `sessionId`.

## Implementation References

- **Session store:** `erk_shared/extraction/claude_code_session_store/`
- **Parent ID extraction:** `real.py:_extract_parent_session_id()`
- **Agent type extraction:** `show_cmd.py:extract_agent_types()`
- **Session-scoped discovery:** `preprocess_session.py:discover_agent_logs()`
