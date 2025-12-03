---
title: Claude Code Session Layout
read_when:
  - "working with session logs"
  - "parsing session logs"
  - "understanding ~/.claude/projects/ structure"
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

**Implementation:** See `encode_path_to_project_folder()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/find_project_dir.py:87-108`

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

**Discovery:**

```python
from pathlib import Path

def find_session_logs(project_dir: Path) -> list[Path]:
    """Find all main session logs (exclude agent logs)."""
    return [
        f for f in project_dir.glob("*.jsonl")
        if f.is_file() and not f.name.startswith("agent-")
    ]
```

### Agent Subprocess Logs

**Pattern:** `agent-<agent-id>.jsonl`

**Characteristics:**

- One file per agent subprocess
- Agent types: `devrun`, `Plan`, `Explore`, `gt-update-pr-submitter`, etc.
- Contains agent-specific tool calls and results
- Linked to parent session via `sessionId` field

**Discovery:**

```python
def discover_agent_logs(project_dir: Path) -> list[Path]:
    """Find all agent subprocess logs."""
    return sorted(project_dir.glob("agent-*.jsonl"))
```

**Implementation:** See `discover_agent_logs()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/debug_agent.py:92`

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

**Extraction Code:**

```python
def get_session_id_from_env() -> str | None:
    """Extract session ID from SESSION_CONTEXT env var."""
    session_context = os.environ.get("SESSION_CONTEXT")
    if not session_context:
        return None

    if "session_id=" in session_context:
        parts = session_context.split("session_id=")
        if len(parts) == 2:
            return parts[1].strip()

    return None
```

**Implementation:** See `get_session_id_from_env()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/debug_agent.py:20-39`

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

**Extraction from Filename:**

```python
agent_id = log_path.stem.replace("agent-", "")
# agent-17cfd3f4.jsonl → 17cfd3f4
```

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

You can identify compaction boundaries by looking for `type: "summary"` entries:

```python
def find_compaction_boundaries(entries: list[dict]) -> list[int]:
    """Find indices where context compaction occurred."""
    return [
        i for i, entry in enumerate(entries)
        if entry.get("type") == "summary"
    ]
```

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

```python
import os
from pathlib import Path

def get_scratch_dir() -> Path | None:
    """Get scratch directory that persists across compactions."""
    session_id = get_current_session_id()
    if not session_id:
        return None

    scratch_dir = Path.home() / ".erk" / "scratch" / session_id
    scratch_dir.mkdir(parents=True, exist_ok=True)
    return scratch_dir


def save_work_state(state: dict) -> None:
    """Save state that survives context compaction."""
    scratch = get_scratch_dir()
    if scratch:
        state_file = scratch / "work_state.json"
        state_file.write_text(json.dumps(state))


def restore_work_state() -> dict | None:
    """Restore state after context compaction."""
    scratch = get_scratch_dir()
    if not scratch:
        return None

    state_file = scratch / "work_state.json"
    if state_file.exists():
        return json.loads(state_file.read_text())

    return None
```

## Key Algorithms

### Finding Project Directory for Path

**Use Case:** Get session logs for a specific filesystem path

**Algorithm:**

1. Encode the filesystem path using replacement rules
2. Construct path: `~/.claude/projects/<encoded-path>`
3. Check if directory exists

**Code Example:**

```python
from pathlib import Path

def find_project_dir(working_dir: str) -> Path | None:
    """Find Claude project directory for a filesystem path."""
    # Encode path
    encoded = "-" + working_dir.replace("/", "-").replace(".", "-").lstrip("-")

    # Construct project directory path
    project_dir = Path.home() / ".claude" / "projects" / encoded

    if not project_dir.exists():
        return None

    return project_dir
```

**Implementation:** See `find_project_info()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/find_project_dir.py:111-174`

### Finding Project Directory for Session ID

**Use Case:** Locate session logs when you only have the session ID

**Algorithm:**

1. Iterate through all project directories in `~/.claude/projects/`
2. For each directory, scan `*.jsonl` files
3. Read first 10 lines of each file
4. Parse JSON and check if `sessionId` field matches
5. Return project directory when match found

**Code Example:**

```python
import json
from pathlib import Path

def find_project_dir_for_session(session_id: str) -> Path | None:
    """Find project directory containing a specific session."""
    projects_base = Path.home() / ".claude" / "projects"

    if not projects_base.exists():
        return None

    # Iterate all project directories
    for project_dir in projects_base.iterdir():
        if not project_dir.is_dir():
            continue

        # Check session files
        for session_file in project_dir.glob("*.jsonl"):
            if session_file.name.startswith("agent-"):
                continue

            # Check first few lines for session ID
            try:
                with open(session_file, encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        if i >= 10:  # Only check first 10 lines
                            break

                        try:
                            entry = json.loads(line)
                            if entry.get("sessionId") == session_id:
                                return project_dir
                        except json.JSONDecodeError:
                            continue
            except OSError:
                continue

    return None
```

**Implementation:** See `find_project_dir_for_session()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/debug_agent.py:42-80`

### Discovering Latest Session

**Use Case:** Find the most recent session in a project

**Algorithm:**

1. Glob all `*.jsonl` files in project directory
2. Filter out files starting with `agent-`
3. Sort by modification time (most recent first)
4. Extract session ID from filename (`.stem`)

**Code Example:**

```python
from pathlib import Path

def find_latest_session(project_dir: Path) -> str | None:
    """Return most recent session ID by modification time."""
    session_files = [
        f for f in project_dir.glob("*.jsonl")
        if f.is_file() and not f.name.startswith("agent-")
    ]

    if not session_files:
        return None

    latest = max(session_files, key=lambda f: f.stat().st_mtime)
    return latest.stem
```

**Implementation:** Part of `find_project_info()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/find_project_dir.py:148-174`

### Correlating Agent Logs with Session

**Method 1: Session ID Matching**

Agent logs contain `sessionId` field linking them to the parent session:

```python
def filter_agent_entries(entries: list[dict], session_id: str) -> list[dict]:
    """Filter agent log entries by session ID."""
    return [
        entry for entry in entries
        if entry.get("sessionId") == session_id
    ]
```

**Method 2: Temporal Correlation (Plan Agents)**

Plan agents are matched using timestamp proximity:

- Match agent log timestamps within 1 second of Task tool invocations
- Used specifically for Plan subagents
- See `discover_planning_agent_logs()` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/preprocess_session.py:542-623`

### Reading Session Entries

**Code Example:**

```python
import json
from pathlib import Path

def read_session_entries(
    session_file: Path,
    session_id: str | None = None
) -> list[dict]:
    """Parse JSONL file and optionally filter by session ID."""
    entries = []

    with open(session_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue  # Skip malformed lines

            # Filter by session ID if provided
            if session_id is not None:
                entry_session = entry.get("sessionId")
                if entry_session is not None and entry_session != session_id:
                    continue

            entries.append(entry)

    return entries
```

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

**Handling:**

```python
if entry_session is not None and entry_session != session_id:
    skipped_entries += 1
    continue
```

**Implication:**

- Code handles missing `sessionId` gracefully
- Includes entries without `sessionId` when filtering

### Empty and Warmup Sessions

**Detection Logic:**

- **Empty:** < 3 entries OR no meaningful user/assistant interaction
- **Warmup:** Contains "warmup" keyword in first user message

**Implementation:**

```python
def is_empty_session(entries: list[dict]) -> bool:
    """Check if session is empty (< 3 entries or no interaction)."""
    if len(entries) < 3:
        return True

    has_user = any(e.get("type") == "user" for e in entries)
    has_assistant = any(e.get("type") == "assistant" for e in entries)

    return not (has_user and has_assistant)

def is_warmup_session(entries: list[dict]) -> bool:
    """Check if session is a warmup session."""
    if not entries:
        return False

    first_user = next(
        (e for e in entries if e.get("type") == "user"),
        None
    )

    if not first_user:
        return False

    content = first_user.get("message", {}).get("content", [])
    if not content:
        return False

    text = content[0].get("text", "").lower() if content else ""
    return "warmup" in text
```

**Implementation:** See `preprocess_session.py` in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/`

### Malformed JSONL Entries

**Issue:** Invalid JSON lines in `.jsonl` files

**Handling:**

```python
try:
    entry = json.loads(line)
except json.JSONDecodeError:
    continue  # Skip malformed lines
```

**Best Practice:** Always wrap JSON parsing in try-except blocks

## Code Reference

### Core Modules

| Module                        | Path                                                                           | Purpose                                   |
| ----------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------- |
| `find_project_dir.py`         | `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/` | Project directory discovery and encoding  |
| `debug_agent.py`              | `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/` | Agent log parsing and inspection          |
| `preprocess_session.py`       | `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/` | Session log preprocessing and compression |
| `session_plan_extractor.py`   | `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/`                      | Extract plans from session logs           |
| `session_id_injector_hook.py` | `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/` | Inject session ID into context            |

### Test Files

| Test File                                    | Coverage                               |
| -------------------------------------------- | -------------------------------------- |
| `test_find_project_dir.py`                   | Path encoding, project discovery       |
| `test_debug_agent.py`                        | Agent log parsing, session correlation |
| `test_preprocess_session.py`                 | Session filtering, compression         |
| `test_session_plan_extractor_integration.py` | Plan extraction across sessions        |

## Common Operations

### Get Project Directory for Current Working Directory

```python
from pathlib import Path

def get_claude_project_dir(working_dir: str) -> Path:
    """Get Claude project directory for a filesystem path."""
    claude_base = Path.home() / ".claude" / "projects"
    project_name = "-" + working_dir.replace("/", "-").replace(".", "-").lstrip("-")
    return claude_base / project_name

# Usage
project_dir = get_claude_project_dir("/Users/foo/code/erk")
# Returns: ~/.claude/projects/-Users-foo-code-erk
```

### List All Sessions for a Project

```python
def find_all_sessions(project_dir: Path) -> list[str]:
    """Return list of session IDs (excluding agent logs)."""
    session_files = [
        f for f in project_dir.glob("*.jsonl")
        if f.is_file() and not f.name.startswith("agent-")
    ]
    return [f.stem for f in session_files]
```

### Get Session ID from Environment

```python
import os

def get_current_session_id() -> str | None:
    """Get session ID from SESSION_CONTEXT environment variable."""
    session_context = os.environ.get("SESSION_CONTEXT", "")

    if "session_id=" in session_context:
        parts = session_context.split("session_id=")
        if len(parts) == 2:
            return parts[1].strip()

    return None
```

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
                continue  # Skip malformed lines

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
        # Read first few lines to check session ID
        try:
            with open(agent_file, encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i >= 10:  # Only check first 10 lines
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

### Session Summarization Patterns

Techniques for creating human-readable summaries from session logs.

#### Extract Key Messages

```python
def extract_key_messages(
    entries: list[dict],
    include_tools: bool = False
) -> list[dict]:
    """Extract user and assistant text messages from session entries.

    Args:
        entries: Parsed JSONL entries from session log
        include_tools: Whether to include tool use/result entries

    Returns:
        List of simplified message dicts with type and text
    """
    messages = []

    for entry in entries:
        entry_type = entry.get("type")

        # Skip tool entries unless explicitly requested
        if entry_type == "tool_result" and not include_tools:
            continue

        # Skip summary entries (compaction boundaries)
        if entry_type == "summary":
            continue

        message = entry.get("message", {})
        content = message.get("content", [])

        # Extract text content
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

#### Identify Compaction Boundaries

```python
def split_by_compaction(entries: list[dict]) -> list[list[dict]]:
    """Split session entries into segments separated by compaction.

    Each segment represents a "generation" of the conversation
    before context was summarized.

    Returns:
        List of entry lists, one per conversation segment
    """
    segments = []
    current_segment = []

    for entry in entries:
        if entry.get("type") == "summary":
            # Save current segment and start new one
            if current_segment:
                segments.append(current_segment)
            current_segment = [entry]  # Include summary in new segment
        else:
            current_segment.append(entry)

    # Don't forget the last segment
    if current_segment:
        segments.append(current_segment)

    return segments
```

#### Create Session Summary

```python
def summarize_session(session_file: Path) -> dict:
    """Create a structured summary of a session.

    Returns:
        Dict with session metadata and key events
    """
    entries = parse_session_log(session_file)

    if not entries:
        return {"error": "Empty session"}

    # Basic metadata
    session_id = entries[0].get("sessionId", "unknown")
    first_timestamp = None
    last_timestamp = None

    for entry in entries:
        ts = entry.get("message", {}).get("timestamp")
        if ts:
            if first_timestamp is None:
                first_timestamp = ts
            last_timestamp = ts

    # Count entry types
    type_counts = {}
    for entry in entries:
        t = entry.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    # Find compaction count
    compaction_count = type_counts.get("summary", 0)

    # Extract user requests (first line of each user message)
    user_requests = []
    for entry in entries:
        if entry.get("type") == "user":
            content = entry.get("message", {}).get("content", [])
            for item in content:
                if item.get("type") == "text":
                    text = item.get("text", "").strip()
                    # Take first line as summary
                    first_line = text.split("\n")[0][:100]
                    if first_line:
                        user_requests.append(first_line)
                    break

    return {
        "session_id": session_id,
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
        "total_entries": len(entries),
        "type_counts": type_counts,
        "compaction_count": compaction_count,
        "user_requests": user_requests[:10],  # First 10 requests
    }
```

#### Find Session by ID and Summarize

```python
def summarize_session_by_id(session_id: str) -> dict | None:
    """Find and summarize a session by its ID.

    Searches all project directories for the session.
    """
    # Find project directory containing this session
    project_dir = find_project_dir_for_session(session_id)
    if not project_dir:
        return None

    # Find the session file
    session_file = project_dir / f"{session_id}.jsonl"
    if not session_file.exists():
        # Try without extension (session ID might be filename)
        for f in project_dir.glob("*.jsonl"):
            if f.stem == session_id:
                session_file = f
                break
        else:
            return None

    return summarize_session(session_file)
```

#### Example Output

```python
summary = summarize_session_by_id("abc123-def456")
print(summary)
# {
#     "session_id": "abc123-def456",
#     "first_timestamp": 1700000000.0,
#     "last_timestamp": 1700003600.0,
#     "total_entries": 245,
#     "type_counts": {
#         "user": 23,
#         "assistant": 45,
#         "tool_result": 177,
#         "summary": 2
#     },
#     "compaction_count": 2,
#     "user_requests": [
#         "Run pytest tests",
#         "Fix the failing test in test_auth.py",
#         "Add type hints to the User class",
#         ...
#     ]
# }
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
