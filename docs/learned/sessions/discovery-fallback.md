---
title: Session Discovery and Fallback Patterns
read_when:
  - "implementing session analysis or learn workflows"
  - "handling missing or unavailable session files"
  - "choosing between session discovery commands"
tripwires:
  - action: "using get-session-metadata or get-session-for-issue exec commands"
    warning: "These commands do not exist. Use 'erk exec list-sessions' for general enumeration or 'erk exec get-learn-sessions' for plan-specific discovery."
  - action: "assuming a session ID from metadata corresponds to a file on disk"
    warning: "Claude Code manages session lifecycle; old sessions may be cleaned up. Always use LBYL discovery before reading."
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# Session Discovery and Fallback Patterns

## Core Principle

**Always discover what's available before assuming availability.** Session files are session-scoped — Claude Code may clean them up at any time, so a session ID from GitHub metadata may not correspond to a file on disk. Discovery commands exist specifically to bridge this gap.

## Two Discovery Paths

Erk has two distinct session discovery commands that serve different purposes. Choosing the wrong one wastes tokens or misses available sessions.

| Command                               | Purpose                                             | Output                                        | When to use                                                |
| ------------------------------------- | --------------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------- |
| `erk exec list-sessions`              | Enumerate all sessions for the current project      | JSON with branch context and session metadata | General session browsing, selecting sessions interactively |
| `erk exec get-learn-sessions <issue>` | Find sessions associated with a specific plan issue | JSON with categorized session IDs and paths   | Learn workflows, plan-specific analysis                    |

### Why two commands?

`list-sessions` knows nothing about plans — it scans the local Claude Code project directory and returns what's there. `get-learn-sessions` starts from a plan issue, extracts session IDs from GitHub metadata (plan-header fields and issue comments), then checks which ones are actually readable on disk. It also discovers remote sessions (branch-based or legacy artifact-based) that `list-sessions` would never find.

<!-- Source: packages/erk-shared/src/erk_shared/sessions/discovery.py, find_sessions_for_plan -->

See `find_sessions_for_plan()` in `packages/erk-shared/src/erk_shared/sessions/discovery.py` for how plan-specific discovery extracts session IDs from multiple metadata sources (plan-header fields, impl-started/impl-ended comments, learn-invoked comments).

## Output Schema (list-sessions)

The `erk exec list-sessions` command returns a JSON object. Key structure:

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
  "filtered_count": 3
}
```

## Fallback Hierarchy for Learn Workflows

When a learn workflow needs session data, the ideal source (planning session) is often unavailable because it was created in a different Claude Code session. The discovery system degrades through multiple levels rather than failing.

| Priority | Source                    | How discovered                                                                          | Why it might be missing                                             |
| -------- | ------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| 1        | Planning session          | `created_from_session` in plan-header                                                   | Created in a prior Claude Code session, since cleaned up            |
| 2        | Implementation session    | `last_local_impl_session` in plan-header + issue comments                               | Same reason — different session lifecycle                           |
| 3        | Remote session (branch)   | `last_session_branch` in plan-header                                                    | Branch may have been deleted; requires checkout step                |
| 4        | Remote session (artifact) | `last_remote_impl_run_id` in plan-header                                                | Legacy path; GitHub Actions artifacts expire after 90 days          |
| 5        | Local fallback scan       | `find_local_sessions_for_project()` scans project directory, filtered by current branch | No metadata link to plan, but recent sessions may still be relevant |
| 6        | Skip analysis             | Always available                                                                        | Produces no session insights, but workflow continues                |

<!-- Source: src/erk/cli/commands/exec/scripts/get_learn_sessions.py, _discover_sessions -->

The fallback logic is implemented in `_discover_sessions()` in `src/erk/cli/commands/exec/scripts/get_learn_sessions.py`. The critical design decision: local fallback scanning only triggers when **no** GitHub-tracked sessions are readable on disk, preventing noisy irrelevant sessions from diluting plan-specific results.

### Branch Filtering in Local Fallback

When the local fallback scan activates, sessions are filtered by the current git branch name. Each session's JSONL log contains a `gitBranch` field, and only sessions whose branch matches the current worktree branch are included. This prevents worktree slot reuse from contaminating results — when a worktree is reused for a different plan, old sessions from a previous branch are excluded even though they exist in the same project directory.

### Anti-pattern: Hard failure on missing session

Never `exit 1` or raise when a session file is unavailable. The entire fallback hierarchy exists because session availability is inherently unreliable. Log a warning and degrade to the next level.

### Anti-pattern: Skipping discovery and reading session files directly

Don't construct session paths manually (e.g., `~/.claude/projects/.../sessions/{id}.jsonl`). The `ClaudeInstallation` ABC provides `find_session_globally()` for existence checks — use it. Direct path construction bypasses the abstraction and breaks if Claude Code changes its storage layout.

## Related Documentation

- [Session Lifecycle](lifecycle.md) — Session file persistence, availability patterns, and LBYL principles
- [Session Preprocessing](preprocessing.md) — Token limits and multi-part file handling
