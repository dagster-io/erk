---
title: Claude Code Session Layout
read_when:
  - "working with session logs"
  - "parsing session logs"
  - "understanding ~/.claude/projects/ structure"
  - "debugging session lookup issues"
  - "implementing features that depend on project directory resolution"
last_audited: "2026-02-03 04:00 PT"
audit_result: edited
---

# Claude Code Session Layout

Complete reference for the `~/.claude/projects/` directory structure and session log format used by Claude Code.

## Directory Structure

### Project Directory Encoding

Project directories use **deterministic path encoding**:

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

**Implementation:**

- Primary: `encode_path_to_project_folder()` in `src/erk/cli/commands/exec/scripts/find_project_dir.py`
- Session extraction: `_get_project_dir()` in `packages/erk-shared/src/erk_shared/gateway/claude_installation/real.py`

## JSONL Format Specification

### Entry Structure

Each line is a JSON object representing one entry in the conversation:

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

| Field           | Type   | Description                  | Notes                                |
| --------------- | ------ | ---------------------------- | ------------------------------------ |
| `sessionId`     | string | UUID identifying the session | Used to correlate agent logs         |
| `type`          | string | Entry type                   | `user`, `assistant`, `tool_result`   |
| `message`       | object | Message content              | Structure varies by type             |
| `timestamp`     | float  | Unix timestamp               | In `message` object, for correlation |
| `gitBranch`     | string | Current git branch           | Optional metadata                    |
| `usage`         | object | Token usage statistics       | Typically stripped during processing |
| `file-snapshot` | object | File state capture           | For file history tracking            |
| `slug`          | string | Plan mode identifier         | Maps to `~/.claude/plans/{slug}.md`  |

### Entry Types

| Type                    | Description                                      |
| ----------------------- | ------------------------------------------------ |
| `user`                  | Human input AND tool results (as content blocks) |
| `assistant`             | Claude responses with text and tool_use blocks   |
| `summary`               | Context compaction markers                       |
| `system`                | Notifications and system events                  |
| `file-history-snapshot` | File state tracking                              |
| `queue-operation`       | Message queue manipulations                      |

## Slug and Plan Mode Behavior

When Plan Mode is exited (user approves plan), the assistant entry includes a `slug` field identifying the saved plan:

```json
{
  "parentUuid": "parent_002",
  "sessionId": "abc11111-2222-3333-4444-555555555555",
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

- **Location**: The `slug` field appears as a top-level field on `type: "assistant"` entries
- **Timing**: Added when Plan Mode is exited (plan approved and saved)
- **Value**: Corresponds to plan filename without `.md` extension
- **Plan file**: `~/.claude/plans/{slug}.md`

**Session-scoped plan lookup:**

The slug field enables session-scoped plan extraction:

1. Parse session JSONL for entries matching the current `sessionId`
2. Find assistant entries with a `slug` field
3. Use the most recent slug to locate the plan file

**Implementation:** See `extract_slugs_from_session()` in `packages/erk-shared/src/erk_shared/gateway/claude_installation/real.py`

## Session Lifecycle and Compaction

### Session ID Persistence

**Key Insight:** Session IDs persist across context compactions and summarizations.

When a Claude Code conversation runs out of context window space, the system:

1. Summarizes earlier parts of the conversation
2. Continues with a condensed context
3. **Keeps the same session ID**

This means:

- A single session log file can contain multiple "generations" of conversation
- Scratch files at `.erk/scratch/sessions/<session-id>/` remain accessible after compaction
- Agent subprocesses spawned before and after compaction share the same parent session ID

### Compaction Boundary Detection

Compaction boundaries are identified by `type: "summary"` entries in the JSONL log. When context is compacted, a summary entry is inserted marking the boundary between the condensed history and new conversation.

### Implications for Tooling

- Tools that track session state should handle compaction gracefully
- Don't assume all context from earlier in the session is available
- Scratch files persist and can bridge compaction boundaries
- Use scratch storage for data that must survive context loss

See `erk_shared/scratch/scratch.py:get_scratch_dir()` for the canonical implementation.

## Key Algorithms

### Finding Project Directory for Path (with Walk-Up Search)

**Algorithm:**

1. Start with the given path (resolved to absolute)
2. Encode the path using replacement rules (see "Project Directory Encoding" above)
3. Construct path: `~/.claude/projects/<encoded-path>`
4. Check if directory exists
5. If not found, walk up to the parent directory
6. Repeat steps 2-5 until finding a match or hitting the filesystem root

**Why walk-up?** This enables running erk commands from subdirectories of a Claude project. If you start Claude Code in `/Users/dev/myrepo` but later `cd` into `/Users/dev/myrepo/src/components`, the walk-up search finds the parent project.

**Implementation:** See `RealClaudeCodeSessionStore._get_project_dir()` in `packages/erk-shared/src/erk_shared/gateway/claude_code_session_store/real.py`

### cwd_hint Optimization Pattern

**Problem:** Finding a project directory by session ID requires scanning all project directories in `~/.claude/projects/`. With many projects (e.g., 1,476 directories), this takes 378ms-1.6s.

**Solution:** Pass a `cwd_hint` parameter to enable O(1) lookup. When provided, the function encodes the hint to compute the project directory directly, then verifies the session exists there before falling back to full scan.

**Performance comparison:**

| Scenario            | Time Complexity | Typical Time         |
| ------------------- | --------------- | -------------------- |
| Without cwd_hint    | O(n)            | 378ms-1.6s (n=1,476) |
| With correct hint   | O(1)            | ~0.1ms               |
| With incorrect hint | O(n)            | Same as without      |

**When to use cwd_hint:** Always provide it when the working directory is available. The function gracefully falls back to full scan if hint is wrong. No penalty for providing an incorrect hint.

**Implementation:** See `_get_project_dir()` in `packages/erk-shared/src/erk_shared/gateway/claude_installation/real.py`

## Special Cases and Quirks

### Hidden Directories (Dot Directories)

Leading dots in directory names become double dashes:

```
/Users/foo/.config    → -Users-foo--config
/Users/foo/.erk       → -Users-foo--erk
/Users/foo/.cache     → -Users-foo--cache
```

### Backward Compatibility

Older logs may not have `sessionId` field. When filtering entries by session ID, treat entries without a `sessionId` field as belonging to any session (include them). Only skip entries that have a `sessionId` that doesn't match the target.

### Empty and Warmup Sessions

**Detection Logic:**

- **Empty:** < 3 entries OR no meaningful user/assistant interaction
- **Warmup:** Contains "warmup" keyword in first user message

**Implementation:** See `is_empty_session()` in `src/erk/cli/commands/exec/scripts/preprocess_session.py`

### Warmup Agents (Deep Dive)

Warmup agents are internal initialization subprocesses spawned by Claude Code for prompt cache pre-warming.

When Claude Code spawns subagents via the Task tool, it may first spawn minimal "warmup" tasks to pre-populate the prompt cache. This is part of Claude Code's prompt caching optimization.

**Characteristics:**

| Property           | Warmup Agent          | Real Work Agent         |
| ------------------ | --------------------- | ----------------------- |
| File size          | 444B - 2KB            | 15KB - 50KB+            |
| First user message | "Warmup"              | Actual task description |
| Useful content     | None                  | Tool calls, results     |
| Parent linkage     | Has `sessionId` field | Has `sessionId` field   |

**Why they exist:** Prompt caching in Claude Code works by saving model state after processing common prefixes. Warmup agents pre-populate this cache so subsequent real subagent calls experience lower latency.

**Identifying warmup agents:**

1. File starts with `agent-` prefix
2. First user message contains "Warmup"
3. Very small file size (< 3KB)
4. No meaningful tool calls or outputs

### Malformed JSONL Entries

Invalid JSON lines in `.jsonl` files should be skipped gracefully during parsing. Always wrap JSON parsing in try-except blocks to handle corrupt entries.

## Related Documentation

- [JSONL Schema Reference](./jsonl-schema-reference.md) - Comprehensive entry types, content blocks, and tool schemas
- [Agent Type Extraction](./agent-type-extraction.md) - Extracting agent metadata from sessions
- [Session Hierarchy](./session-hierarchy.md) - Understanding session relationships
