---
title: Session File Lifecycle and Persistence
read_when:
  - "working with Claude Code sessions"
  - "implementing learn workflows"
  - "accessing planning session files"
tripwires:
  - action: "accessing planning session in learn workflow"
    warning: "Session files are session-scoped, not persistent across Claude Code sessions. If planning session is unavailable, implement fallback strategy using available sessions."
last_audited: "2026-02-05 13:55 PT"
audit_result: edited
---

# Session File Lifecycle and Persistence

Critical understanding of session file persistence and availability patterns.

## Table of Contents

- [Core Principle: Session-Scoped Persistence](#core-principle-session-scoped-persistence)
- [Session File Locations](#session-file-locations)
- [When Session Files Are Missing](#when-session-files-are-missing)
- [Fallback Principles](#fallback-principles)
- [Session Preprocessing](#session-preprocessing)
- [Learn Workflow Implications](#learn-workflow-implications)

---

## Core Principle: Session-Scoped Persistence

**Session files persist only within the current Claude Code session.**

- **Lifetime:** From session start to session end (not guaranteed beyond)
- **Scope:** Single Claude Code conversation
- **Storage:** `~/.claude/projects/<project>/sessions/<session_id>.jsonl`

**Critical implication:** Session files are **not guaranteed** to exist across different Claude Code sessions. Claude Code manages session storage lifecycle, and old sessions may be cleaned up. Erk cannot control this policy.

---

## Session File Locations

### Standard Session Files

Session JSONL files live in `~/.claude/projects/<project>/sessions/`. Use `erk exec list-sessions` to enumerate available sessions with metadata (timestamps, summaries, branch context). See `list_sessions.py` in `src/erk/cli/commands/exec/scripts/` for the full implementation.

### Uploaded Sessions (Gist-Based)

Sessions can be uploaded to GitHub Gists for persistent cross-session access via `erk exec upload-session`. This creates a secret gist containing the session JSONL, and optionally updates the plan-header metadata in the associated GitHub issue with the gist URL. See `upload_session.py` in `src/erk/cli/commands/exec/scripts/` for options and behavior.

### Scratch Storage

`.erk/scratch/sessions/<session-id>/` is used for **inter-process file passing within a session** (e.g., preprocessed XML files, hook data). It is not a session archive. These directories are cleaned up by `cleanup_stale_scratch()` after 1 hour. See `erk_shared.scratch.scratch` for the implementation.

---

## When Session Files Are Missing

### Different Claude Code Session

If you are in a **different** Claude Code session from when planning occurred:

- Planning session file may not exist in `~/.claude/projects/<project>/sessions/`
- Only the current session and recent sessions are available
- Historical sessions are not guaranteed to persist

### Example Scenario

1. **Monday 10am:** User creates plan (session `abc123`)
2. **Monday 11am:** Plan saved to GitHub issue
3. **Tuesday 2pm:** User starts new Claude Code session (session `def456`)
4. **Tuesday 2:15pm:** `/erk:learn` command runs
5. **Result:** Session `abc123` file may not exist in filesystem

---

## Fallback Principles

### Principle 1: Always Check Before Access (LBYL)

Verify session file exists before attempting to read. Never assume a session ID from metadata corresponds to a file on disk.

### Principle 2: Discover What Is Available

Use `erk exec get-learn-sessions <issue-number>` to discover all sessions for a plan issue. This returns planning session IDs, implementation session IDs, readable (on-disk) session IDs, and remote gist-based sessions. See `get_learn_sessions.py` in `src/erk/cli/commands/exec/scripts/` for the full discovery logic including local fallback scanning.

### Principle 3: Graceful Degradation

Missing sessions should **never** cause complete workflow failure. Reduce scope and continue:

- If planning session is unavailable, use implementation session
- If no tracked sessions exist, scan local sessions as fallback
- If no sessions at all, skip session analysis and continue with other data sources

### Principle 4: Anti-Pattern -- Hard Failure

Do not `exit 1` on a missing session. Log a warning and continue with available data.

---

## Session Preprocessing

Session preprocessing compresses JSONL to XML format via `erk exec preprocess-session`. Key behaviors:

- **Compression:** Achieves ~75-84% size reduction (JSONL to compact XML)
- **Chunking:** Use `--max-tokens` to split output into multiple XML files when sessions exceed Claude's read limit
- **Output naming:** `{prefix}-{session-id}.xml` or `{prefix}-{session-id}-part{N}.xml` for multi-part output

For full details on compression metrics, output modes, and chunking algorithm, see [Session Preprocessing](preprocessing.md) and `preprocess_session.py` in `src/erk/cli/commands/exec/scripts/`.

---

## Learn Workflow Implications

### Planning Session Access

Learn workflows ideally access both the **planning session** (where the plan was created) and the **implementation session** (where code was written). But the planning session may not be available.

### Session Discovery for Learn

Use `erk exec get-learn-sessions <issue-number>` to discover sessions for a plan. This command:

1. Queries GitHub issue metadata for tracked session IDs
2. Checks which sessions exist locally (readable)
3. Falls back to scanning local sessions if no tracked sessions are readable
4. Reports remote gist-based sessions that can be downloaded

The learn workflow should use whichever sessions are available, prioritizing by quality but accepting partial data over failure.

---

## Related Documentation

- [Session Discovery and Fallback](discovery-fallback.md) - Session enumeration and fallback strategies
- [Session Preprocessing](preprocessing.md) - Token limits and multi-part file handling
- [Plan Lifecycle](../planning/lifecycle.md) - Plan storage and session references
