# Session Analysis Tools

Complete reference for kit CLI commands and jq recipes for analyzing Claude Code session logs.

## Kit CLI Commands

All commands invoked via `dot-agent run erk <command>`.

### list-sessions

List sessions for the current worktree with metadata.

```bash
dot-agent run erk list-sessions [--limit N] [--min-size BYTES]
```

**Options:**

| Option       | Default | Description                                        |
| ------------ | ------- | -------------------------------------------------- |
| `--limit`    | 10      | Maximum sessions to return                         |
| `--min-size` | 0       | Minimum file size in bytes (filters tiny sessions) |

**Output:**

```json
{
  "success": true,
  "branch_context": {
    "current_branch": "feature-branch",
    "trunk_branch": "main",
    "is_on_trunk": false
  },
  "current_session_id": "abc123-def456",
  "sessions": [
    {
      "session_id": "abc123-def456",
      "mtime_display": "Dec 3, 11:38 AM",
      "mtime_relative": "2h ago",
      "mtime_unix": 1701612500.0,
      "size_bytes": 125000,
      "summary": "how many sessions...",
      "is_current": true
    }
  ],
  "project_dir": "/Users/foo/.claude/projects/-Users-foo-code-myapp",
  "filtered_count": 3
}
```

---

### preprocess-session

Convert raw JSONL session log to compressed XML format.

```bash
dot-agent run erk preprocess-session <log-path> [OPTIONS]
```

**Options:**

| Option                                 | Description                           |
| -------------------------------------- | ------------------------------------- |
| `--session-id ID`                      | Filter entries to specific session ID |
| `--include-agents/--no-include-agents` | Include agent logs (default: True)    |
| `--no-filtering`                       | Disable all filtering optimizations   |
| `--stdout`                             | Output to stdout instead of temp file |

**Filtering Applied:**

- Empty session detection (< 3 entries or no meaningful content)
- Warmup session filtering
- Documentation deduplication (replaces duplicates with hash markers)
- Tool parameter truncation (>200 chars truncated with path-aware `...`)
- Tool result pruning (first 30 lines, preserves error-containing lines)
- Log discovery operation filtering (pwd, ls, find, echo commands)

**Output:**

- Default: Prints path to temp XML file
- With `--stdout`: XML directly to stdout
- Compression metrics printed to stderr

**XML Elements:**

- `<session id="...">` - Session container
- `<user>` - User messages
- `<assistant>` - Assistant responses
- `<tool_use name="..." id="...">` - Tool invocations
- `<tool_result id="...">` - Tool outputs

---

### extract-latest-plan

Extract the latest plan from session files.

```bash
dot-agent run erk extract-latest-plan [--session-id SESSION_ID]
```

**Options:**

| Option         | Description                            |
| -------------- | -------------------------------------- |
| `--session-id` | Session ID to search within (optional) |

**Search Logic:**

1. If session_id provided: Searches for `slug` field in session entries
2. Looks up plan files in `~/.claude/plans/{slug}.md`
3. Falls back to most recently modified plan by mtime

**Output:**

- Success: Plan text on stdout (exit code 0)
- Failure: Error message on stderr (exit code 1)

---

### create-issue-from-session

Extract plan from session and create GitHub issue.

```bash
dot-agent run erk create-issue-from-session [--session-id SESSION_ID]
```

**Output:**

```json
{
  "success": true,
  "issue_number": 123,
  "issue_url": "https://github.com/owner/repo/issues/123",
  "title": "Plan: Feature implementation"
}
```

Or on failure:

```json
{
  "success": false,
  "error": "No plan found for session"
}
```

---

### render-session-content

Render session XML as GitHub comment blocks with automatic chunking.

```bash
dot-agent run erk render-session-content --session-file <path> [OPTIONS]
```

**Options:**

| Option               | Description                           |
| -------------------- | ------------------------------------- |
| `--session-file`     | Path to session XML file (required)   |
| `--session-label`    | Label for session (e.g., branch name) |
| `--extraction-hints` | Comma-separated extraction hints      |

**Output:**

```json
{
  "success": true,
  "blocks": ["<details>...</details>", "..."],
  "chunk_count": 2
}
```

**Chunking:**

- GitHub comment limit: 65,536 bytes
- Safety buffer: 1,000 bytes
- Line-aware splitting to avoid breaking mid-line
- Chunk numbers added for multi-chunk content

---

### extract-session-from-issue

Extract session XML content from GitHub issue comments.

```bash
dot-agent run erk extract-session-from-issue <issue-number> [OPTIONS]
```

**Options:**

| Option         | Description                                                  |
| -------------- | ------------------------------------------------------------ |
| `--output`     | Output path for session XML (default: auto in .erk/scratch/) |
| `--session-id` | Session ID for scratch directory                             |

**Output:**

```json
{
  "success": true,
  "issue_number": 123,
  "session_file": "/path/to/.erk/scratch/sessions/abc123/session.xml",
  "session_ids": ["abc123-def456"],
  "chunk_count": 2
}
```

**Behavior:**

- Fetches all comments from issue
- Parses session-content metadata blocks
- Handles chunked content by combining in order
- Writes combined XML to output file

---

## Additional erk CLI Commands

### erk find-project-dir

Find Claude project directory for a filesystem path.

```bash
erk find-project-dir [PATH]
```

**Output:**

```json
{
  "project_dir": "/Users/foo/.claude/projects/-Users-foo-code-myapp",
  "latest_session": "abc123-def456",
  "session_count": 5
}
```

---

## Slash Commands

### /erk:sessions-list

Display formatted table of recent sessions.

**Output format:**

```
Session ID   Date                 Relative   Summary
───────────────────────────────────────────────────────────────
4f852cdc     Dec 3, 11:38 AM      2h ago     how many session ids... (current)
d8f6bb38     Dec 3, 11:35 AM      2h ago     no rexporting due to...
```

### /erk:analyze-context

Analyze context window usage across sessions.

**Output includes:**

- Summary metrics (sessions analyzed, peak context, cache hit rate)
- Token breakdown by category (file reads, tool results, etc.)
- Duplicate file reads with wasted token estimates

---

## jq Analysis Recipes

### Count Tool Calls by Type

```bash
cat session.jsonl | jq -s '
  [.[] | select(.type == "assistant") |
   .message.content[]? | select(.type == "tool_use") | .name] |
  group_by(.) | map({tool: .[0], count: length}) |
  sort_by(-.count)
'
```

### Sum Tool Result Sizes

```bash
cat session.jsonl | jq -s '
  [.[] | select(.type == "tool_result") |
   (.message.content[0].text // "" | length)] |
  {total_chars: add, count: length, avg: (add / length | floor)}
'
```

### Find Large Tool Results (Top 10)

```bash
cat session.jsonl | jq -c '
  select(.type == "tool_result") |
  {
    tool_id: .message.tool_use_id,
    size: (.message.content[0].text // "" | length)
  }
' | jq -s 'sort_by(-.size) | .[0:10]'
```

### Extract User Messages

```bash
cat session.jsonl | jq -r '
  select(.type == "user") |
  .message.content[0].text
'
```

### Find First User Message (Session Summary)

```bash
cat session.jsonl | jq -rs '
  [.[] | select(.type == "user")] | .[0] |
  .message.content[0].text | .[0:100]
'
```

### Find Agent Logs for Session

```bash
SESSION_ID="abc123-def456"
PROJECT_DIR=$(erk find-project-dir | jq -r '.project_dir')

for f in "$PROJECT_DIR"/agent-*.jsonl; do
  if head -10 "$f" | jq -e "select(.sessionId == \"$SESSION_ID\")" > /dev/null 2>&1; then
    echo "$f"
  fi
done
```

### Check for Errors in Agent Log

```bash
cat agent-*.jsonl | jq 'select(.message.is_error == true)'
```

### Extract Tool Usage Timeline

```bash
cat session.jsonl | jq -c '
  select(.type == "assistant") |
  .message.content[]? | select(.type == "tool_use") |
  {name, id}
'
```

### Count Messages by Type

```bash
cat session.jsonl | jq -s '
  group_by(.type) | map({type: .[0].type, count: length})
'
```

### Find Plans Created in Session (via slug field)

```bash
cat session.jsonl | jq -r '
  select(.type == "assistant" and .slug != null) |
  .slug
'
```

### Get Token Usage Statistics

```bash
cat session.jsonl | jq -s '
  [.[] | select(.type == "assistant") | .message.usage | select(. != null)] |
  {
    total_input: [.[].input_tokens] | add,
    total_output: [.[].output_tokens] | add,
    cache_read: [.[].cache_read_input_tokens // 0] | add,
    cache_creation: [.[].cache_creation_input_tokens // 0] | add
  }
'
```

### Find Compaction Boundaries (Summary Entries)

```bash
cat session.jsonl | jq 'select(.type == "summary")'
```

---

## Common Workflows

### Debug Context Blowout

1. Find session log:

   ```bash
   erk find-project-dir
   ```

2. Count total tool result sizes:

   ```bash
   cat session.jsonl | jq -s '[.[] | select(.type == "tool_result") | .message.content[0].text | length] | add'
   ```

3. Find largest results (see recipe above)

4. Look for patterns:
   - Many Read operations → use Explore agent
   - Large Glob results → narrow patterns
   - Repeated file reads → caching opportunity

### Debug Agent Failure

1. Find agent logs:

   ```bash
   ls -lt $(erk find-project-dir | jq -r '.project_dir')/agent-*.jsonl | head -5
   ```

2. Check for errors:

   ```bash
   cat agent-*.jsonl | jq 'select(.message.is_error == true)'
   ```

3. View agent conversation:
   ```bash
   dot-agent run erk preprocess-session agent-<id>.jsonl --stdout | head -200
   ```

### Compare Session Sizes

```bash
PROJECT_DIR=$(erk find-project-dir | jq -r '.project_dir')
ls -lhS "$PROJECT_DIR"/*.jsonl | grep -v agent- | head -20
```

### Find Sessions by Content

```bash
PROJECT_DIR=$(erk find-project-dir | jq -r '.project_dir')
grep -l "specific text" "$PROJECT_DIR"/*.jsonl | grep -v agent-
```

### Extract Plan from Specific Session

```bash
dot-agent run erk extract-latest-plan --session-id abc123-def456
```

### Full Extraction Workflow

```bash
# 1. List sessions and find the one to extract from
dot-agent run erk list-sessions --limit 20

# 2. Preprocess to XML
dot-agent run erk preprocess-session /path/to/session.jsonl --stdout > session.xml

# 3. Render as GitHub comment blocks
dot-agent run erk render-session-content --session-file session.xml

# 4. Or create issue directly
dot-agent run erk create-issue-from-session --session-id abc123
```
