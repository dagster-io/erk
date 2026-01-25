---
title: Agent Session Files
read_when:
  - "reading or extracting data from agent session files"
  - "working with agent subprocesses in Claude sessions"
  - "implementing session log parsing"
tripwires:
  - action: "reading or extracting data from agent session files"
    warning: 'Agent session files use `agent-` prefix and require dedicated reading logic. Check `session_id.startswith("agent-")` and route to `_read_agent_session_entries()`. Using generic `_iter_session_entries()` skips agent files silently.'
---

# Agent Session Files

Agent session files are separate JSONL files created when Claude Code spawns subagent tasks via the Task tool. They require special handling during session analysis.

## File Naming

| Type         | Naming Pattern       | Example                |
| ------------ | -------------------- | ---------------------- |
| Main session | `{session-id}.jsonl` | `abc123def.jsonl`      |
| Agent log    | `agent-{uuid}.jsonl` | `agent-17cfd3f4.jsonl` |

Both types reside in the same Claude project directory (`~/.claude/projects/{encoded-path}/`).

## Why Agent Sessions Are Different

Agent sessions are isolated files containing complete conversation logs for a single subagent. Unlike main session files where entries from multiple sessions may be interleaved, agent files contain only that agent's entries.

**Key insight**: When reading agent files, you read the entire file without filtering by `sessionId`. For main session files, you must filter by `sessionId` since multiple sessions share the file.

## Detection Pattern

Check the session ID prefix to route to appropriate reading logic:

```
session_id.startswith("agent-")
    ├─ TRUE  → Read entire file, no filtering needed
    └─ FALSE → Filter by sessionId field in entries
```

## Reading Agent Sessions

Main sessions require filtering by `sessionId` in each entry. Agent sessions do not:

- **Main session**: Parse all entries, keep only those where `entry["sessionId"] == target_session_id`
- **Agent session**: Read all entries from `agent-{id}.jsonl` directly

## Implementation Reference

The canonical implementation is `_read_agent_session_entries()` in:

```
packages/erk-shared/src/erk_shared/learn/extraction/claude_installation/real.py
```

This method:

1. Checks if session ID starts with `agent-`
2. Constructs path to agent file (`project_dir / f"{session_id}.jsonl"`)
3. Reads all entries without filtering

## Why This Matters for /erk:learn

The learn workflow processes session logs to extract insights. If agent logs are read with the wrong method:

- Using `_iter_session_entries()` with agent ID → Returns empty (no matching `sessionId` in generic parsing)
- Using `_read_agent_session_entries()` → Returns all agent entries correctly

This was a source of bugs where agent logs were silently skipped during learn extraction.

## Discovering Agent Logs for a Session

Agent logs belonging to a parent session can be discovered by:

1. Globbing for `agent-*.jsonl` in the project directory
2. Reading the first entry of each file
3. Checking if `sessionId` matches the parent session
4. Or checking if timestamp correlation indicates the agent was spawned during the session

See `discover_agent_logs()` in `preprocess_session.py` for the full discovery logic.

## Related Documentation

- [Parallel Session Awareness](parallel-session-awareness.md) - Session scoping patterns
- [Session Layout](layout.md) - Claude project directory structure
