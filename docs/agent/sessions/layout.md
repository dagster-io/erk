---
title: Claude Code Session Layout
read_when:
  - "working with session logs"
  - "parsing session logs"
  - "understanding ~/.claude/projects/ structure"
  - "debugging session lookup issues"
  - "implementing features that depend on project directory resolution"
---

# Claude Code Session Layout

Complete reference for the `~/.claude/projects/` directory structure and session log format used by Claude Code.

## Table of Contents

- [Overview](#overview)
- [Directory Structure](#directory-structure)
- [File Types](#file-types)
- [JSONL Format Specification](#jsonl-format-specification)
- [Session and Agent IDs](#session-and-agent-ids)
- [Key Algorithms](#key-algorithms)
- [Special Cases and Quirks](#special-cases-and-quirks)
- [Code Reference](#code-reference)
- [Common Operations](#common-operations)
- [Examples](#examples)

## Overview

Claude Code stores session logs and agent subprocess logs in `~/.claude/projects/`. Each project directory contains:

- **Main session logs**: The primary conversation thread (`<session-id>.jsonl`)
- **Agent logs**: Subprocess execution logs (`agent-<agent-id>.jsonl`)

These JSONL files enable:

- Session replay and analysis
- Agent debugging and inspection
- Plan extraction from conversations
- Performance monitoring and cost tracking

## Directory Structure

### Base Location

```
~/.claude/projects/
```

All session logs are stored under this directory, organized by project path.

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

- Primary: `encode_path_to_project_folder()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/find_project_dir.py:87-108`
- Session extraction: `_encode_path_to_project_folder()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/session_plan_extractor.py:17-28` (uses cwd_hint optimization)

### Complete Directory Tree

```
~/.claude/
└── projects/
    ├── -Users-foo-code-myapp/
    │   ├── session-abc123.jsonl         # Main session log
    │   ├── session-def456.jsonl         # Another session
    │   ├── agent-17cfd3f4.jsonl        # devrun agent log
    │   ├── agent-2a3b4c5d.jsonl        # Plan agent log
    │   └── agent-9e8f7g6h.jsonl        # gt agent log
    ├── -Users-foo--config-app/
    │   └── session-xyz789.jsonl
    └── ...
```

## File Types

### Main Session Logs

**Pattern:** `<session-id>.jsonl`

**Characteristics:**

- One file per Claude Code session
- Session ID is the filename (without `.jsonl` extension)
- Contains the main conversation thread
- Includes user messages, assistant responses, and tool results

**Discovery:** Main session logs are `.jsonl` files in the project directory that don't start with `agent-`. Use `erk kit exec erk list-sessions` to list sessions for the current project.

### Agent Subprocess Logs

**Pattern:** `agent-<agent-id>.jsonl`

**Characteristics:**

- One file per agent subprocess
- Agent types: `devrun`, `Plan`, `Explore`, `gt-update-pr-submitter`, etc.
- Contains agent-specific tool calls and results
- Linked to parent session via `sessionId` field

**Discovery:** Agent logs match the pattern `agent-*.jsonl` in the project directory.

See `preprocess_session.py:discover_agent_logs()` for the canonical implementation.

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

#### User Entry

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

#### Assistant Entry with Tool Use

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

#### Tool Result Entry

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

#### File History Snapshot Entry

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

#### Plan Mode Entry (with slug)

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

**Implementation:** See `extract_slugs_from_session()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/session_plan_extractor.py:101-148`

## Session and Agent IDs

### Session ID Format

**Characteristics:**

- UUID-like strings (format not strictly enforced)
- Examples: `abc123-def456`, `2024-11-23-session`
- Used as filename (without `.jsonl` extension)
- Injected into agent context via `SESSION_CONTEXT` environment variable

**Environment Variable Format:**

```bash
SESSION_CONTEXT="session_id=abc123-def456"
```

**Extraction:** The session ID appears after `session_id=` in the environment variable value. Parse by splitting on this prefix.

See `erk_shared/extraction/session_discovery.py:get_current_session_id()` for the canonical implementation.

### Agent ID Format

**Characteristics:**

- Hex/alphanumeric identifiers
- Often truncated to 8 characters for display
- Full ID used in filenames

**Examples:**

```
17cfd3f4
2a3b4c5d
9e8f7g6h
```

**Extraction from Filename:** Remove the `agent-` prefix from the filename stem. Example: `agent-17cfd3f4.jsonl` → `17cfd3f4`

## Session Lifecycle and Compaction

Understanding how sessions evolve over time, especially during context compaction.

### Session ID Persistence

**Key Insight:** Session IDs persist across context compactions and summarizations.

When a Claude Code conversation runs out of context window space, the system:

1. Summarizes earlier parts of the conversation
2. Continues with a condensed context
3. **Keeps the same session ID**

This means:

- A single session log file can contain multiple "generations" of conversation
- The session ID in `SESSION_CONTEXT` environment variable remains constant
- Scratch files at `.erk/scratch/<session-id>/` remain accessible after compaction
- Agent subprocesses spawned before and after compaction share the same parent session ID

### What Happens During Compaction

```
Before Compaction:
┌─────────────────────────────────────────────────┐
│ Session: abc-123                                │
│ Entry 1: user message                           │
│ Entry 2: assistant response                     │
│ Entry 3: tool result                            │
│ ... (many entries)                              │
│ Entry 500: user message                         │
│ [Context window full]                           │
└─────────────────────────────────────────────────┘

After Compaction:
┌─────────────────────────────────────────────────┐
│ Session: abc-123  (SAME ID!)                    │
│ Entry 501: type="summary" (condensed history)   │
│ Entry 502: user message (continues normally)    │
│ Entry 503: assistant response                   │
│ ...                                             │
└─────────────────────────────────────────────────┘
```

### Compaction Boundary Detection

Compaction boundaries are identified by `type: "summary"` entries in the JSONL log. When context is compacted, a summary entry is inserted marking the boundary between the condensed history and new conversation.

### Implications for Tooling

**Session-Aware Tools:**

- Tools that track session state should handle compaction gracefully
- Don't assume all context from earlier in the session is available
- Scratch files persist and can bridge compaction boundaries

**Agent Spawning:**

- Agents spawned before compaction have access to full pre-compaction context
- Agents spawned after compaction only see the summarized context
- Both share the same parent session ID for correlation

**Scratch Storage:**

- Files at `.erk/scratch/<session-id>/` persist across compactions
- Use scratch storage for data that must survive context loss
- Session ID remains valid for the entire session lifetime

### Example: Cross-Compaction Work

To persist data across context compactions, use the session-scoped scratch directory at `.erk/scratch/sessions/<session-id>/`. This directory remains accessible throughout the session lifetime, even after compaction.

See `erk_shared/scratch/scratch.py:get_scratch_dir()` for the canonical implementation.

## Key Algorithms

### Finding Project Directory for Path (with Walk-Up Search)

**Use Case:** Get session logs for a specific filesystem path

**Algorithm:**

1. Start with the given path (resolved to absolute)
2. Encode the path using replacement rules (see "Project Directory Encoding" above)
3. Construct path: `~/.claude/projects/<encoded-path>`
4. Check if directory exists
5. If not found, walk up to the parent directory
6. Repeat steps 2-5 until finding a match or hitting the filesystem root

**Why walk-up?** This enables running erk commands from subdirectories of a Claude project. If you start Claude Code in `/Users/dev/myrepo` but later `cd` into `/Users/dev/myrepo/src/components`, the walk-up search finds the parent project.

**CLI:** Use `erk kit exec erk find-project-dir` to find the project directory for the current working directory.

**Implementation:** See `RealClaudeCodeSessionStore._get_project_dir()` in `packages/erk-shared/src/erk_shared/extraction/claude_code_session_store/real.py`

### Finding Project Directory for Session ID

**Use Case:** Locate session logs when you only have the session ID

**Algorithm:**

1. Iterate through all project directories in `~/.claude/projects/`
2. For each directory, scan `*.jsonl` files (excluding `agent-*` files)
3. Read first 10 lines of each file
4. Parse JSON and check if `sessionId` field matches
5. Return project directory when match found

**Implementation:** See `find_project_dir_for_session()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/session_plan_extractor.py`

### cwd_hint Optimization Pattern

**Use Case:** Accelerate session lookup when the working directory is known

**Problem:** Finding a project directory by session ID requires scanning all project directories in `~/.claude/projects/`. With many projects (e.g., 1,476 directories), this takes 378ms-1.6s.

**Solution:** Pass a `cwd_hint` parameter to enable O(1) lookup. When provided, the function encodes the hint to compute the project directory directly, then verifies the session exists there before falling back to full scan.

**Performance comparison:**

| Scenario            | Time Complexity | Typical Time         |
| ------------------- | --------------- | -------------------- |
| Without cwd_hint    | O(n)            | 378ms-1.6s (n=1,476) |
| With correct hint   | O(1)            | ~0.1ms               |
| With incorrect hint | O(n)            | Same as without      |

**When to use cwd_hint:**

- **Always provide it** when the working directory is available (e.g., from environment)
- The function gracefully falls back to full scan if hint is wrong
- No penalty for providing an incorrect hint (just loses the optimization)

**Where cwd_hint is available:**

- CLI commands: `Path.cwd()` or command arguments
- Kit commands: Working directory from context
- Agent subprocesses: `cwd` field in session log entries

**Implementation:** See `find_project_dir_for_session()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/session_plan_extractor.py:65-98`

### Discovering Latest Session

**Use Case:** Find the most recent session in a project

**Algorithm:**

1. Glob all `*.jsonl` files in project directory
2. Filter out files starting with `agent-`
3. Sort by modification time (most recent first)
4. Extract session ID from filename (`.stem`)

**CLI:** Use `erk kit exec erk find-project-dir` which outputs the latest session ID.

**Implementation:** Part of `find_project_info()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/find_project_dir.py`

### Correlating Agent Logs with Session

**Method 1: Session ID Matching**

Agent logs contain a `sessionId` field linking them to the parent session. Filter entries by matching this field against the target session ID.

**Method 2: Temporal Correlation (Plan Agents)**

Plan agents are matched using timestamp proximity:

- Match agent log timestamps within 1 second of Task tool invocations
- Used specifically for Plan subagents
- See `discover_planning_agent_logs()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/preprocess_session.py:542-623`

### Reading Session Entries

Session logs are JSONL format (one JSON object per line). To parse:

1. Read file line by line
2. Strip whitespace and skip empty lines
3. Parse each line as JSON (skip malformed lines gracefully)
4. Optionally filter by `sessionId` field

For quick inspection, use `jq` or Python's `json` module directly on the command line.

## Special Cases and Quirks

### Hidden Directories (Dot Directories)

**Issue:** Leading dots in directory names become double dashes

**Examples:**

```
/Users/foo/.config    → -Users-foo--config
/Users/foo/.erk       → -Users-foo--erk
/Users/foo/.cache     → -Users-foo--cache
```

**Why:** The encoding rule treats `.` like any other dot in the path

### Agent Subprocess Sessions

**Key Insight:** Agent logs can contain complete subsessions

- Plan agents create plans (ExitPlanMode tool calls)
- Agent logs must be searched when extracting plans
- Agent logs have their own `sessionId` (parent session ID)

**Implication:** When extracting data (e.g., plans), check both:

1. Main session logs
2. Agent logs linked to that session

### Backward Compatibility

**Issue:** Older logs may not have `sessionId` field

**Handling:** When filtering entries by session ID, treat entries without a `sessionId` field as belonging to any session (include them). Only skip entries that have a `sessionId` that doesn't match the target.

**Implication:**

- Code handles missing `sessionId` gracefully
- Includes entries without `sessionId` when filtering

See `preprocess_session.py` for the canonical implementation.

### Empty and Warmup Sessions

**Detection Logic:**

- **Empty:** < 3 entries OR no meaningful user/assistant interaction
- **Warmup:** Contains "warmup" keyword in first user message

**Implementation:** See `is_empty_session()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/preprocess_session.py`

### Malformed JSONL Entries

**Issue:** Invalid JSON lines in `.jsonl` files

**Handling:** Skip malformed lines gracefully during parsing. Always wrap JSON parsing in try-except blocks to handle corrupt entries.

## Code Reference

### Core Modules

| Module                        | Path                                                                           | Purpose                                   |
| ----------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------- |
| `find_project_dir.py`         | `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/` | Project directory discovery and encoding  |
| `preprocess_session.py`       | `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/` | Session log preprocessing and compression |
| `session_plan_extractor.py`   | `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/`                      | Extract plans from session logs           |
| `session_id_injector_hook.py` | `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/` | Inject session ID into context            |

### Test Files

| Test File                                    | Coverage                         |
| -------------------------------------------- | -------------------------------- |
| `test_find_project_dir.py`                   | Path encoding, project discovery |
| `test_preprocess_session.py`                 | Session filtering, compression   |
| `test_session_plan_extractor_integration.py` | Plan extraction across sessions  |

## Common Operations

### Quick Session Listing

List sessions by modification time to find recent activity:

```bash
# Find project directory for current path
erk kit exec erk find-project-dir

# Example output:
# Project: -Users-schrockn--erk-repos-erk
# Path: /Users/schrockn/.claude/projects/-Users-schrockn--erk-repos-erk
# Latest session: abc123-def456
```

List sessions sorted by modification time:

```bash
ls -lt ~/.claude/projects/-Users-schrockn--erk-repos-erk/*.jsonl | head -20
```

**File Size to Message Count Correlation:**

| File Size | Approximate Messages |
| --------- | -------------------- |
| 10 KB     | ~5-10 messages       |
| 50 KB     | ~25-50 messages      |
| 100 KB    | ~50-100 messages     |
| 500 KB    | ~200-400 messages    |

These are rough estimates. Actual counts depend on:

- Message length
- Tool output verbosity
- Number of tool calls per turn

### Get Project Directory for Current Working Directory

Use `erk kit exec erk find-project-dir` to get the project directory for the current path. The directory path is constructed by encoding the working directory path (see "Project Directory Encoding" above).

### List All Sessions for a Project

Session IDs are the filenames (stems) of `.jsonl` files that don't start with `agent-`.

**CLI:** Use `erk kit exec erk list-sessions` to list sessions for the current project.

### Get Session ID from Environment

The session ID is available in the `SESSION_CONTEXT` environment variable, formatted as `session_id=<uuid>`.

**Implementation:** See `get_current_session_id()` in `erk_shared/extraction/session_discovery.py`

### Parse Session Log

Session logs are JSONL format. Parse line by line, skipping empty and malformed lines.

**Quick inspection with jq:**

```bash
cat session.jsonl | jq -s 'length'  # Count entries
cat session.jsonl | jq -s '.[0]'    # First entry
```

### Find Agent Logs for Session

Agent logs are linked to parent sessions via the `sessionId` field. To find agent logs for a session, glob `agent-*.jsonl` files and check the first few entries for a matching `sessionId`.

**Implementation:** See `discover_planning_agent_logs()` in `preprocess_session.py`

### Session Summarization Patterns

Session summarization involves extracting key information from session logs:

- **Extract key messages:** Filter entries by type, extract text content from `message.content`
- **Identify compaction boundaries:** Look for `type: "summary"` entries
- **Count entry types:** Aggregate entries by `type` field
- **Extract user requests:** Get first line of each `type: "user"` entry's text content

These patterns are useful for session analysis and debugging. For automated analysis, use:

```bash
/erk:analyze-context
```

## Examples

### Real-World Directory Structure

```
~/.claude/projects/
├── -Users-schrockn--erk-repos-erk/
│   ├── 2024-11-23-morning-session.jsonl     # Main session (123 KB)
│   ├── 2024-11-23-afternoon-session.jsonl   # Another session (456 KB)
│   ├── agent-17cfd3f4.jsonl                 # devrun agent (23 KB)
│   ├── agent-2a3b4c5d.jsonl                 # Plan agent (12 KB)
│   └── agent-9e8f7g6h.jsonl                 # gt agent (8 KB)
│
├── -Users-schrockn--erk-repos-erk-worktrees-fix-bug-123/
│   ├── bugfix-session.jsonl                 # Main session (89 KB)
│   └── agent-abc12345.jsonl                 # devrun agent (15 KB)
│
└── -Users-schrockn-code-myapp/
    ├── session-xyz.jsonl                    # Main session (234 KB)
    └── agent-def67890.jsonl                 # Explore agent (45 KB)
```

### Typical File Sizes

Based on production usage:

- **Main sessions:** 50-500 KB (before compression)
- **Agent logs:** 5-50 KB
- **Compressed XML:** 30-70% size reduction

### Sample Session Log Content

```jsonl
{"sessionId":"abc123","type":"user","message":{"content":[{"type":"text","text":"Run pytest tests"}],"timestamp":1700000000.0}}
{"sessionId":"abc123","type":"assistant","message":{"content":[{"type":"text","text":"I'll run the tests"},{"type":"tool_use","name":"Bash","id":"tool1","input":{"command":"pytest"}}],"timestamp":1700000001.0}}
{"sessionId":"abc123","type":"tool_result","message":{"tool_use_id":"tool1","content":[{"type":"text","text":"Exit code 0\n===== 42 passed ====="}],"is_error":false,"timestamp":1700000002.0}}
```

### Sample Agent Log Content

```jsonl
{"sessionId":"abc123","type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash","id":"tool2","input":{"command":"make fast-ci"}}],"timestamp":1700000003.0}}
{"sessionId":"abc123","type":"tool_result","message":{"tool_use_id":"tool2","content":[{"type":"text","text":"All checks passed"}],"is_error":false,"timestamp":1700000004.0}}
```

## Summary of Key Points

1. **Deterministic Encoding:** Project paths are encoded using simple character replacement (`/` → `-`, `.` → `-`)

2. **Two File Types:** Main session logs (`<session-id>.jsonl`) and agent logs (`agent-<agent-id>.jsonl`)

3. **Session Correlation:** Agent logs contain parent `sessionId` field for correlation

4. **JSONL Format:** One JSON object per line, with standardized fields (`type`, `message`, `sessionId`)

5. **Latest Session:** Determined by file modification time, excluding agent logs

6. **Error Handling:** Graceful degradation for missing fields, malformed JSON, and missing directories

7. **Hidden Directories:** Leading dots create double dashes (`.config` → `--config`)

8. **Backward Compatibility:** Code handles logs with/without `sessionId` field

9. **Discovery Patterns:** Project directories discovered by encoding; sessions discovered by globbing `*.jsonl`

10. **Agent Subsessions:** Agent logs can contain complete subsessions (e.g., Plan agents creating plans)

## Related Documentation

- [Agent Debugging](./debugging.md) - Debugging agent execution
- [Planning Workflow](./planning-workflow.md) - Working with plans and sessions
- [CLI Output Styling](./cli-output-styling.md) - Formatting output from session data
