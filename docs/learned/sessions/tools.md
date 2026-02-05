---
title: Session Log Analysis Tools
read_when:
  - "finding session logs"
  - "inspecting agent execution"
  - "debugging session issues"
last_audited: "2026-02-05 13:56 PT"
audit_result: edited
---

# Session Log Analysis Tools

CLI commands and recipes for inspecting Claude Code session logs.

## Available CLI Commands

### erk exec find-project-dir

Find the Claude project directory for a filesystem path.

```bash
# From current directory
erk exec find-project-dir

# For specific path
erk exec find-project-dir --path /path/to/project
```

**Output:**

```json
{
  "success": true,
  "project_dir": "/Users/foo/.claude/projects/-Users-foo-code-erk",
  "cwd": "/Users/foo/code/erk",
  "encoded_path": "-Users-foo-code-erk",
  "session_logs": ["abc123.jsonl", "agent-17cfd3f4.jsonl"],
  "latest_session_id": "abc123"
}
```

**Source:** `src/erk/cli/commands/exec/scripts/find_project_dir.py`

### erk exec list-sessions

Discover Claude Code sessions for the current worktree.

```bash
# List sessions for current worktree
erk exec list-sessions [--limit N] [--min-size BYTES] [--session-id ID]
```

**Output format:**

```json
{
  "success": true,
  "branch_context": {
    "current_branch": "feature-branch",
    "trunk_branch": "master",
    "is_on_trunk": false
  },
  "current_session_id": "abc123-def456",
  "sessions": [
    {
      "session_id": "abc123-def456",
      "mtime_display": "Dec 3, 11:38 AM",
      "mtime_relative": "2h ago",
      "mtime_unix": 1733250000.0,
      "size_bytes": 125000,
      "summary": "Implement feature XYZ",
      "is_current": true,
      "branch": "feature-branch",
      "session_path": "/Users/foo/.claude/projects/-Users-foo-code-erk/abc123-def456.jsonl"
    }
  ],
  "project_dir": "claude-code-project",
  "filtered_count": 3
}
```

**Fields:**

- `success`: Whether the operation succeeded
- `branch_context`: Current branch info and trunk detection (`current_branch`, `trunk_branch`, `is_on_trunk`)
- `current_session_id`: ID passed via `--session-id` CLI option
- `sessions`: List of session objects with:
  - `session_id`, `mtime_display`, `mtime_relative`, `mtime_unix`: Identification and timestamps
  - `size_bytes`, `summary`: Size and first user message excerpt
  - `is_current`: Whether this matches the `--session-id` argument
  - `branch`: Git branch active during the session (extracted from session content)
  - `session_path`: Absolute path to the session `.jsonl` file
- `project_dir`: Abstract project directory identifier
- `filtered_count`: Number of tiny sessions filtered out (below `--min-size`)

**Source:** `src/erk/cli/commands/exec/scripts/list_sessions.py`

**Branch context detection:**

The `branch_context` field provides information about whether the current branch is trunk (main/master) or a feature branch. This affects command behavior:

- **On trunk**: `is_on_trunk=true` - Used for baseline operations
- **On feature branch**: `is_on_trunk=false` - Used for feature development workflows

**Use cases:**

- Finding sessions for extraction plans (`/erk:create-extraction-plan`)
- Session discovery workflows (`/erk:sessions-list`)
- Branch-aware command behavior

### /erk:analyze-context (Slash Command)

Analyzes context window usage across all sessions in the current worktree.

```bash
/erk:analyze-context
```

**Output:**

- Summary metrics (sessions analyzed, peak context, cache hit rate)
- Token breakdown by category (file reads, assistant output, tool results, etc.)
- Duplicate file reads across sessions with wasted token estimates

**Use cases:**

- Understanding why sessions ran out of context
- Identifying optimization opportunities
- Finding duplicate file reads that waste tokens

### erk exec preprocess-session

Converts raw JSONL session logs to readable XML format for analysis.

```bash
erk exec preprocess-session <session-file.jsonl> --stdout
```

**Useful for:**

- Extracting tool usage patterns
- Analyzing conversation flow
- Mining subagent outputs for documentation extraction

**Example:**

```bash
erk exec preprocess-session ~/.claude/projects/.../abc123.jsonl --stdout | head -500
```

## Finding Session Logs

Use `erk exec find-project-dir` for the project directory and `erk exec list-sessions` for session discovery. These commands replace manual shell recipes. For example:

```bash
# Get project directory and latest session
erk exec find-project-dir

# List sessions with metadata, branch info, and file paths
erk exec list-sessions --limit 20 --min-size 1000
```

For searching by session ID across all projects:

```bash
SESSION_ID="abc123-def456"
find ~/.claude/projects -name "${SESSION_ID}.jsonl" 2>/dev/null
```

## Analysis Recipes

Use `erk exec preprocess-session` to convert raw JSONL to readable XML, then analyze. For context-level analysis, use the `/erk:analyze-context` slash command.

For ad-hoc jq analysis on raw JSONL files:

### Count Tool Calls by Type

```bash
SESSION_LOG="path/to/session.jsonl"

cat "$SESSION_LOG" | jq -s '
  [.[] | select(.type == "assistant") |
   .message.content[]? | select(.type == "tool_use") | .name] |
  group_by(.) | map({tool: .[0], count: length}) |
  sort_by(-.count)
'
```

### Find Large Tool Results

```bash
cat "$SESSION_LOG" | jq -c '
  select(.type == "tool_result") |
  {
    tool_id: .message.tool_use_id,
    size: (.message.content[0].text // "" | length)
  }
' | jq -s 'sort_by(-.size) | .[0:10]'
```

## Debugging Workflows

### Session Blew Out Context

1. Find the session log:

   ```bash
   erk exec find-project-dir
   ```

2. Count tool result sizes:

   ```bash
   cat session.jsonl | jq -s '[.[] | select(.type == "tool_result") | .message.content[0].text | length] | add'
   ```

3. Identify top consumers:

   ```bash
   # See "Find Large Tool Results" recipe above
   ```

4. Check for patterns:
   - Many Read operations → use Explore agent
   - Large Glob results → narrow patterns
   - Command loaded multiple times → check command size

See [context-analysis.md](context-analysis.md) for optimization strategies.

### Agent Subprocess Failed

1. Find agent logs for session:

   ```bash
   SESSION_ID="abc123-def456"
   PROJECT_DIR=$(erk exec find-project-dir | jq -r '.project_dir')
   ls -lt "$PROJECT_DIR"/agent-*.jsonl | head -5
   ```

2. Check for errors in log:
   ```bash
   cat agent-<id>.jsonl | jq 'select(.message.is_error == true)'
   ```

### Plan Not Extracted

1. Check if plan was created in agent subprocess:

   ```bash
   # Look for ExitPlanMode tool calls in agent logs
   grep -l "ExitPlanMode" ~/.claude/projects/-*-*/agent-*.jsonl
   ```

2. Verify session ID correlation:
   ```bash
   # Agent log should have matching sessionId
   head -5 agent-*.jsonl | jq '.sessionId'
   ```

## Session Log Format Reference

For complete documentation of the JSONL format, entry types, and field specifications, see [layout.md](layout.md).

Key points:

- One JSON object per line
- Entry types: `user`, `assistant`, `tool_result`, `file-history-snapshot`
- Agent logs prefixed with `agent-`
- Session ID in `sessionId` field links agent logs to parent

## Related Documentation

- [layout.md](layout.md) - Complete format specification
- [context-analysis.md](context-analysis.md) - Analyzing context consumption
- [context-optimization.md](context-optimization.md) - Patterns for reducing context waste
