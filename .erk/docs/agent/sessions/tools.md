---
title: Session Log Analysis Tools
read_when:
  - "finding session logs"
  - "inspecting agent execution"
  - "debugging session issues"
---

# Session Log Analysis Tools

CLI commands and recipes for inspecting Claude Code session logs.

## Available CLI Commands

### erk find-project-dir

Find the Claude project directory for a filesystem path.

```bash
# From current directory
erk find-project-dir

# For specific path
erk find-project-dir /path/to/project
```

**Output:**

```json
{
  "project_dir": "/Users/foo/.claude/projects/-Users-foo-code-myapp",
  "latest_session": "abc123-def456",
  "session_count": 5
}
```

### erk kit exec erk list-sessions

Discover Claude Code sessions for the current worktree (kit CLI command).

```bash
# List sessions for current worktree
erk kit exec erk list-sessions [--limit N] [--min-size BYTES]
```

**Output format:**

```json
{
  "branch_context": {
    "is_on_trunk": false,
    "current_branch": "feature-branch",
    "trunk_branch": "main"
  },
  "current_session_id": "abc123-def456",
  "sessions": [
    {
      "session_id": "abc123-def456",
      "mtime_display": "2h ago",
      "size_bytes": 125000,
      "summary": "125KB"
    }
  ],
  "project_dir": "/Users/foo/.claude/projects/-Users-foo-code-myapp",
  "filtered_count": 3
}
```

**Fields:**

- `branch_context`: Current branch info and trunk detection
- `current_session_id`: ID passed via `--session-id` CLI option
- `sessions`: List with `session_id`, `mtime_display`, `size_bytes`, `summary`
- `project_dir`: Path to session log files
- `filtered_count`: Number of tiny sessions filtered out (below `--min-size`)

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

### erk kit exec erk preprocess-session

Converts raw JSONL session logs to readable XML format for analysis.

```bash
erk kit exec erk preprocess-session <session-file.jsonl> --stdout
```

**Useful for:**

- Extracting tool usage patterns
- Analyzing conversation flow
- Mining subagent outputs for documentation extraction

**Example:**

```bash
erk kit exec erk preprocess-session ~/.claude/projects/.../abc123.jsonl --stdout | head -500
```

## Finding Session Logs

### By Current Directory

```bash
# Get project directory
PROJECT_DIR=$(erk find-project-dir | jq -r '.project_dir')

# List all sessions
ls -lt "$PROJECT_DIR"/*.jsonl | grep -v agent-
```

### By Session ID

If you have a session ID but don't know the project:

```bash
# Search all projects for session ID
SESSION_ID="abc123-def456"
find ~/.claude/projects -name "${SESSION_ID}.jsonl" 2>/dev/null
```

### Latest Session

```bash
# Most recently modified session (excluding agent logs)
ls -t ~/.claude/projects/-Users-*/*.jsonl | grep -v agent- | head -1
```

## Analysis Recipes

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

**Sample output:**

```json
[
  { "tool": "Read", "count": 48 },
  { "tool": "Edit", "count": 44 },
  { "tool": "Glob", "count": 10 },
  { "tool": "Task", "count": 5 }
]
```

### Sum Tool Result Sizes

```bash
cat "$SESSION_LOG" | jq -s '
  [.[] | select(.type == "tool_result") |
   (.message.content[0].text // "" | length)] |
  {total_chars: add, count: length, avg: (add / length | floor)}
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

### Extract User Messages

```bash
cat "$SESSION_LOG" | jq -r '
  select(.type == "user") |
  .message.content[0].text
'
```

### Find Agent Logs for Session

```bash
SESSION_ID="abc123-def456"
PROJECT_DIR=$(erk find-project-dir | jq -r '.project_dir')

# Find agent logs that reference this session
for f in "$PROJECT_DIR"/agent-*.jsonl; do
  if head -10 "$f" | jq -e "select(.sessionId == \"$SESSION_ID\")" > /dev/null 2>&1; then
    echo "$f"
  fi
done
```

## Debugging Workflows

### Session Blew Out Context

1. Find the session log:

   ```bash
   erk find-project-dir
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
   PROJECT_DIR=$(erk find-project-dir | jq -r '.project_dir')
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
