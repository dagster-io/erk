---
title: Session Discovery and Fallback Patterns
read_when:
  - "implementing session analysis workflows"
  - "handling missing session files"
  - "enumerating available sessions"
last_audited: "2026-02-05 13:56 PT"
audit_result: edited
tripwires:
  - action: "using get-session-metadata or get-session-for-issue exec commands"
    warning: "These commands do not exist. Use 'erk exec list-sessions' with --limit, --min-size, and --session-id flags only."
---

# Session Discovery and Fallback Patterns

How to enumerate sessions and implement fallback strategies for missing sessions.

## Core Principle

**Always discover what's available before assuming availability.**

Don't assume session files exist. Use `erk exec list-sessions` to enumerate available sessions, then select from the results.

## Session Enumeration

The `erk exec list-sessions` command is the primary discovery tool.

### Available Options

| Flag           | Type   | Default | Description                                 |
| -------------- | ------ | ------- | ------------------------------------------- |
| `--limit`      | int    | 10      | Maximum number of sessions to list          |
| `--min-size`   | int    | 0       | Minimum session size in bytes               |
| `--session-id` | string | None    | Current session ID (for marking as current) |

### Output Schema

The command returns a JSON object with this structure:

```json
{
  "success": true,
  "branch_context": {
    "current_branch": "feature-xyz",
    "trunk_branch": "master",
    "is_on_trunk": false
  },
  "current_session_id": "abc123-def456",
  "sessions": [
    {
      "session_id": "abc123-def456",
      "mtime_display": "Feb 5, 10:30 AM",
      "mtime_relative": "2h ago",
      "mtime_unix": 1738764600.0,
      "size_bytes": 157000,
      "summary": "First 60 chars of first user message...",
      "is_current": true,
      "branch": "feature-xyz",
      "session_path": "/path/to/session.jsonl"
    }
  ],
  "project_dir": "claude-code-project",
  "filtered_count": 3
}
```

Key fields per session: `session_id`, `mtime_display`, `mtime_relative`, `mtime_unix`, `size_bytes`, `summary`, `is_current`, `branch`, `session_path`.

## Fallback Hierarchy

When the ideal session is unavailable, degrade through this hierarchy:

| Priority | Source                      | Availability | Quality |
| -------- | --------------------------- | ------------ | ------- |
| 1        | Planning session (target)   | Low          | Highest |
| 2        | Implementation session      | Medium       | High    |
| 3        | Recent worktree sessions    | High         | Medium  |
| 4        | Scratch storage sessions    | Medium       | High    |
| 5        | No sessions (skip analysis) | Always       | N/A     |

**Principle:** Prioritize by quality, but accept lower quality over failure.

For detailed fallback patterns (check-before-access, graceful degradation, scratch storage lookup, never-fail-entirely), see [Session Lifecycle - Fallback Patterns](lifecycle.md#fallback-patterns).

---

## Related Documentation

- [Session Lifecycle](lifecycle.md) - Session file persistence, availability patterns, and fallback code examples
- [Session Preprocessing](preprocessing.md) - Token limits and multi-part file handling
