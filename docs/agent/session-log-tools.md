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

### erk debug-agent

Inspect agent subprocess logs.

```bash
# List agent logs for current session
erk debug-agent

# Inspect specific agent by ID
erk debug-agent 17cfd3f4

# Show agent log content
erk debug-agent 17cfd3f4 --show-log
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

See [context-window-analysis.md](context-window-analysis.md) for optimization strategies.

### Agent Subprocess Failed

1. Find agent logs:

   ```bash
   erk debug-agent
   ```

2. Inspect specific agent:

   ```bash
   erk debug-agent <agent-id> --show-log
   ```

3. Check for errors in log:
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

For complete documentation of the JSONL format, entry types, and field specifications, see [claude-code-session-layout.md](claude-code-session-layout.md).

Key points:

- One JSON object per line
- Entry types: `user`, `assistant`, `tool_result`, `file-history-snapshot`
- Agent logs prefixed with `agent-`
- Session ID in `sessionId` field links agent logs to parent

## Related Documentation

- [claude-code-session-layout.md](claude-code-session-layout.md) - Complete format specification
- [context-window-analysis.md](context-window-analysis.md) - Analyzing context consumption
