---
title: Claude Code JSONL Schema Reference
read_when:
  - "parsing Claude Code session files"
  - "understanding JSONL entry types"
  - "extracting data from session logs"
  - "building tools that process session transcripts"
  - "debugging session parsing issues"
---

# Claude Code JSONL Schema Reference

Comprehensive reference for the JSONL schema used in Claude Code session logs. This schema is reverse-engineered from community tools and production session analysis.

## Table of Contents

- [Community Tools Reference](#community-tools-reference)
- [Entry Types](#entry-types)
- [Content Block Types](#content-block-types)
- [Tool Input Schemas](#tool-input-schemas)
- [Tool Output Schemas](#tool-output-schemas)
- [Common Metadata Fields](#common-metadata-fields)
- [Agent Session Correlation](#agent-session-correlation)
- [Timestamp Handling](#timestamp-handling)
- [Special Patterns](#special-patterns)
- [Schema Versioning Notes](#schema-versioning-notes)
- [Implementation Notes](#implementation-notes)

## Community Tools Reference

This documentation synthesizes insights from four community projects that parse Claude Code session files:

| Tool                          | Language           | Focus Area                         | Key Insight                                 |
| ----------------------------- | ------------------ | ---------------------------------- | ------------------------------------------- |
| claude-code-log               | Python/Pydantic    | HTML visualization, token tracking | Most comprehensive Pydantic models          |
| claude-code-transcripts       | Python/Jinja2      | Markdown export                    | Content format handling (string vs array)   |
| claude-conversation-extractor | Python             | Search and export                  | Filtering heuristics, relevance scoring     |
| claude-JSONL-browser          | TypeScript/Next.js | Web UI for parsing                 | Double-escape handling, tool type detection |

## Entry Types

### 1. User Entry (`type: "user"`)

Represents human input, tool results, and user-initiated actions.

```json
{
  "parentUuid": "previous_entry_uuid",
  "uuid": "unique_message_uuid",
  "sessionId": "session_uuid",
  "type": "user",
  "message": {
    "role": "user",
    "content": [{ "type": "text", "text": "Run the tests" }]
  },
  "timestamp": "2024-12-15T10:30:00.000Z",
  "cwd": "/Users/dev/project",
  "gitBranch": "feature-branch",
  "isMeta": false,
  "agentId": null
}
```

**Key fields:**

- `isMeta`: `true` for slash commands like `/model`, `/context`
- `agentId`: Set for messages within sub-agent sessions

**Semantic variants (detected via content patterns):**

| Variant              | Detection                                                                       |
| -------------------- | ------------------------------------------------------------------------------- |
| Slash command (meta) | `isMeta: true`                                                                  |
| Slash command (tags) | `<command-name>`, `<command-args>`, `<command-contents>`                        |
| Command output       | `<local-command-stdout>...</local-command-stdout>`                              |
| Bash input           | `<bash-input>...</bash-input>`                                                  |
| Bash output          | `<bash-stdout>`, `<bash-stderr>`                                                |
| Compacted summary    | Starts with "This session is being continued from a previous conversation"      |
| User memory          | `<user-memory-input>...</user-memory-input>`                                    |
| IDE notification     | `<ide_opened_file>`, `<ide_selection>`, `<post-tool-use-hook><ide_diagnostics>` |

### 2. Assistant Entry (`type: "assistant"`)

Represents Claude's responses including text, tool calls, and thinking.

```json
{
  "parentUuid": "previous_entry_uuid",
  "uuid": "unique_message_uuid",
  "sessionId": "session_uuid",
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [
      { "type": "text", "text": "I'll run the tests for you." },
      {
        "type": "tool_use",
        "id": "toolu_abc123xyz",
        "name": "Bash",
        "input": {
          "command": "pytest",
          "description": "Run unit tests"
        }
      }
    ]
  },
  "timestamp": "2024-12-15T10:30:01.000Z",
  "usage": {
    "input_tokens": 1500,
    "output_tokens": 250,
    "cache_read_input_tokens": 1200
  },
  "stop_reason": "tool_use",
  "model": "claude-sonnet-4-20250514",
  "slug": "my-plan-name"
}
```

**Key fields:**

- `usage`: Token consumption statistics
- `stop_reason`: Why generation stopped (`end_turn`, `tool_use`, `max_tokens`)
- `model`: Model identifier used for this response
- `slug`: Plan identifier when Plan Mode is exited (maps to `~/.claude/plans/{slug}.md`)

### 3. Summary Entry (`type: "summary"`)

Marks context compaction boundaries where earlier conversation was summarized.

```json
{
  "type": "summary",
  "summary": "Brief description of conversation topic",
  "leafUuid": "uuid_of_last_message_before_compaction"
}
```

**Key fields:**

- `summary`: Text summarizing the conversation topic
- `leafUuid`: Links to the last message before compaction

### 4. System Entry (`type: "system"`)

Represents notifications, compaction events, and system-level events.

```json
{
  "type": "system",
  "subtype": "compact_boundary",
  "content": "Conversation compacted",
  "level": "info",
  "timestamp": "2024-12-15T10:30:00.000Z",
  "uuid": "unique_message_uuid",
  "sessionId": "session_uuid",
  "compactMetadata": {
    "trigger": "auto",
    "preTokens": 157610
  }
}
```

**Key fields:**

- `level`: Severity (`info`, `warning`, `error`)
- `subtype`: System entry subtype (see table below)
- `content`: Message content (at root level, not in `message` wrapper)
- `compactMetadata`: Present for `compact_boundary` entries

**Observed subtypes:**

| Subtype            | Description                            |
| ------------------ | -------------------------------------- |
| `compact_boundary` | Context compaction event (most common) |
| `local_command`    | Local CLI command output               |
| `informational`    | General informational notifications    |
| `api_error`        | API error events                       |

### 5. Queue Operation (`type: "queue-operation"`)

Represents message queue manipulations (used for steering conversations).

```json
{
  "type": "queue-operation",
  "operation": "dequeue",
  "timestamp": "2024-12-15T10:30:00.000Z",
  "sessionId": "session_uuid"
}
```

**Operations:**

- `enqueue`: Add message to queue
- `dequeue`: Remove from front of queue
- `remove`: Cancel/remove message
- `popAll`: Clear entire queue

### 6. File History Snapshot (`type: "file-history-snapshot"`)

Captures file state at a point in time for tracking changes.

```json
{
  "type": "file-history-snapshot",
  "messageId": "uuid_of_related_message",
  "snapshot": { "...file state data..." },
  "isSnapshotUpdate": false
}
```

**Key fields:**

- `messageId`: UUID linking to the message that triggered this snapshot
- `snapshot`: Object containing file state data
- `isSnapshotUpdate`: Whether this updates a previous snapshot

## Content Block Types

Content blocks appear in the `message.content` array.

### Text Block

```json
{
  "type": "text",
  "text": "Human-readable text content"
}
```

### Tool Use Block

```json
{
  "type": "tool_use",
  "id": "toolu_abc123xyz",
  "name": "ToolName",
  "input": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

**Key fields:**

- `id`: Unique tool invocation ID (prefix `toolu_`)
- `name`: Tool name (e.g., `Bash`, `Read`, `Write`, `Task`)
- `input`: Tool-specific parameters (see [Tool Input Schemas](#tool-input-schemas))

### Tool Result Block

Tool results appear as **content blocks inside `user` entries**, not as top-level entry types. When a tool completes, the result is delivered in a user entry with a `tool_result` content block.

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_abc123xyz",
  "content": "Tool output text or structured data",
  "is_error": false
}
```

**Key fields:**

- `tool_use_id`: Links to the corresponding `tool_use` block
- `content`: Can be string or array of content blocks
- `is_error`: Whether tool execution failed

**Important:** The parent `user` entry may also contain a `toolUseResult` field with additional metadata (e.g., `agentId` for Task tool results).

### Thinking Block

Extended thinking content (for models with thinking capability).

```json
{
  "type": "thinking",
  "thinking": "Internal reasoning process...",
  "signature": "optional_signature"
}
```

### Image Block

Base64-encoded image content.

```json
{
  "type": "image",
  "source": {
    "type": "base64",
    "media_type": "image/png",
    "data": "base64_encoded_data..."
  }
}
```

## Tool Input Schemas

Tool-specific input parameters for common Claude Code tools.

### File Operations

**Read:**

```json
{
  "file_path": "/absolute/path/to/file.py",
  "offset": 0,
  "limit": 2000
}
```

**Write:**

```json
{
  "file_path": "/absolute/path/to/file.py",
  "content": "file contents..."
}
```

**Edit:**

```json
{
  "file_path": "/absolute/path/to/file.py",
  "old_string": "text to replace",
  "new_string": "replacement text",
  "replace_all": false
}
```

**MultiEdit:**

```json
{
  "file_path": "/absolute/path/to/file.py",
  "edits": [
    { "old_string": "first match", "new_string": "first replacement" },
    { "old_string": "second match", "new_string": "second replacement" }
  ]
}
```

**Glob:**

```json
{
  "pattern": "**/*.py",
  "path": "/optional/base/path"
}
```

**Grep:**

```json
{
  "pattern": "regex_pattern",
  "path": "/search/path",
  "glob": "*.py",
  "type": "py",
  "output_mode": "content",
  "multiline": false,
  "head_limit": 100,
  "offset": 0
}
```

### Shell Operations

**Bash:**

```json
{
  "command": "pytest tests/",
  "description": "Run unit tests",
  "timeout": 120000,
  "run_in_background": false,
  "dangerouslyDisableSandbox": false
}
```

### Agent Operations

**Task:**

```json
{
  "prompt": "Detailed task description for sub-agent",
  "subagent_type": "devrun",
  "description": "Short 3-5 word description",
  "model": "sonnet",
  "run_in_background": false,
  "resume": "optional_agent_id_to_resume"
}
```

**TodoWrite:**

```json
{
  "todos": [
    {
      "content": "Task description",
      "status": "pending",
      "activeForm": "Working on task description",
      "id": "optional_id",
      "priority": 1
    }
  ]
}
```

**AskUserQuestion:**

```json
{
  "questions": [
    {
      "question": "Which approach do you prefer?",
      "header": "Approach",
      "options": [
        { "label": "Option A", "description": "Description of option A" },
        { "label": "Option B", "description": "Description of option B" }
      ],
      "multiSelect": false
    }
  ]
}
```

**ExitPlanMode:**

```json
{
  "plan": "The implementation plan content...",
  "launchSwarm": false,
  "teammateCount": 1
}
```

### Web Operations

**WebSearch:**

```json
{
  "query": "search query terms"
}
```

**WebFetch:**

```json
{
  "url": "https://example.com/page",
  "prompt": "Extract specific information from this page"
}
```

## Tool Output Schemas

Common structures returned in tool result content.

**Read output:**

```json
{
  "file_path": "/path/to/file.py",
  "content": "file contents...",
  "start_line": 1,
  "num_lines": 100,
  "total_lines": 500,
  "is_truncated": false,
  "system_reminder": "optional reminder text"
}
```

**Write output:**

```json
{
  "file_path": "/path/to/file.py",
  "success": true,
  "message": "File written successfully"
}
```

**Edit output:**

```json
{
  "file_path": "/path/to/file.py",
  "success": true,
  "diffs": [{ "before": "old text", "after": "new text", "line": 42 }],
  "message": "Edit applied",
  "start_line": 40
}
```

**Bash output:**

```json
{
  "content": "command output...",
  "has_ansi": false
}
```

**Task output:**

```json
{
  "result": "Markdown-formatted agent response..."
}
```

**AskUserQuestion output:**

```json
{
  "answers": [{ "question": "...", "answer": "User's selection" }],
  "raw_message": "Original user input"
}
```

## Common Metadata Fields

Fields that appear across multiple entry types:

| Field               | Type    | Description                                                     | Present In             |
| ------------------- | ------- | --------------------------------------------------------------- | ---------------------- |
| `uuid`              | string  | Unique message identifier                                       | All entries            |
| `parentUuid`        | string  | UUID of preceding message                                       | All entries            |
| `sessionId`         | string  | Session UUID                                                    | All entries            |
| `timestamp`         | various | Entry timestamp (see [Timestamp Handling](#timestamp-handling)) | All entries            |
| `cwd`               | string  | Working directory at time of entry                              | user, assistant        |
| `gitBranch`         | string  | Current git branch                                              | user, assistant        |
| `isSidechain`       | boolean | True for sub-agent messages                                     | user, assistant        |
| `userType`          | string  | User type identifier (e.g., `"external"`)                       | user, assistant        |
| `version`           | string  | Transcript format version (e.g., `"2.0.76"`)                    | First entry in session |
| `isMeta`            | boolean | True for slash commands                                         | user                   |
| `slug`              | string  | Plan mode identifier (maps to `~/.claude/plans/{slug}.md`)      | user, assistant        |
| `thinkingMetadata`  | object  | Thinking level configuration                                    | user                   |
| `todos`             | array   | Current todo list state                                         | user                   |
| `requestId`         | string  | API request correlation ID                                      | assistant              |
| `toolUseResult`     | object  | Tool result metadata including `agentId` for Task results       | user                   |
| `logicalParentUuid` | string  | Parent UUID for branched conversations                          | system                 |
| `compactMetadata`   | object  | Compaction details (`trigger`, `preTokens`)                     | system                 |

## Agent Session Correlation

### Task Invocation Pattern

When the main conversation spawns a sub-agent via the Task tool:

```json
{
  "type": "assistant",
  "message": {
    "content": [
      {
        "type": "tool_use",
        "id": "toolu_task123",
        "name": "Task",
        "input": {
          "prompt": "Run pytest and report results",
          "subagent_type": "devrun",
          "description": "Run tests"
        }
      }
    ]
  }
}
```

### Task Result Pattern

The tool result includes the agent's response:

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_task123",
  "content": "Agent completed task...",
  "is_error": false
}
```

### Agent Log Entry Pattern

Agent subprocess logs are stored in `agent-<agent_id>.jsonl` files. They contain full conversation histories with the same entry structure but include the parent `sessionId`:

```json
{
  "sessionId": "parent_session_uuid",
  "type": "user",
  "message": {
    "content": [{ "type": "text", "text": "Task prompt from parent" }]
  }
}
```

## Timestamp Handling

Claude Code sessions use two timestamp formats:

### Unix Float (older format)

```json
{
  "timestamp": 1700000000.0
}
```

### ISO 8601 String (newer format)

```json
{
  "timestamp": "2024-12-15T10:30:00.000Z"
}
```

### Robust Parsing

Always handle both formats when parsing timestamps:

```python
def parse_timestamp(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Handle ISO 8601
        from datetime import datetime
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.timestamp()
    return None
```

## Special Patterns

### Slash Command Tags

Commands executed via `/command` syntax appear with XML-like tags:

```xml
<command-name>/model</command-name>
<command-message>claude-sonnet-4-20250514</command-message>
<local-command-stdout>Set model to claude-sonnet-4-20250514</local-command-stdout>
```

### Compacted Summary Marker

Sessions that have undergone context compaction contain a marker:

```
This session is being continued from a previous conversation that ran out of context...
```

### IDE Notifications

VSCode/IDE integrations inject structured notifications:

```xml
<ide_opened_file>/path/to/file.py</ide_opened_file>
<ide_selection>{"file": "/path/to/file.py", "start": 10, "end": 20}</ide_selection>
<post-tool-use-hook><ide_diagnostics>...</ide_diagnostics></post-tool-use-hook>
```

### Heredoc Content

Bash commands with heredocs use a specific pattern:

```bash
$(cat <<'EOF'
Multi-line content here
EOF
)
```

**Extraction regex:**

```regex
/\$\(cat\s*<<\s*'?(\w+)'?\s*\n([\s\S]*?)\n\1\s*\)/
```

### Double-Escape Handling

Some content may be double JSON-escaped:

```
"text\\nwith\\nnewlines"        # Single-escaped (normal)
"text\\\\nwith\\\\ndouble"      # Double-escaped (needs extra parse)
```

## Schema Versioning Notes

- **Version field**: First entry in session may include a `version` field indicating transcript format version
- **Backward compatibility**: Entries without `sessionId` are treated as belonging to any session
- **Field additions**: New fields may be added over time; parsers should ignore unknown fields
- **Content flexibility**: `message.content` can be either a string or array of content blocks

## Implementation Notes

### Robust Parsing

Always handle malformed entries gracefully:

```python
def iter_jsonl_entries(content: str):
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue  # Skip malformed lines
```

### Content Extraction

The `content` field can be string or array:

```python
def extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
        return "\n".join(texts)
    return ""
```

### Tool Type Detection

When tool name isn't available, detect by input field combinations:

| Fields Present                            | Tool Type    |
| ----------------------------------------- | ------------ |
| `file_path` + `content`                   | Write        |
| `file_path` + `old_string` + `new_string` | Edit         |
| `file_path` + `edits[]`                   | MultiEdit    |
| `file_path` (alone)                       | Read         |
| `command`                                 | Bash         |
| `query`                                   | WebSearch    |
| `url`                                     | WebFetch     |
| `prompt` + `description`                  | Task         |
| `plan`                                    | ExitPlanMode |

## Related Documentation

- [Session Layout](./layout.md) - Directory structure and file organization
- [Agent Type Extraction](./agent-type-extraction.md) - Extracting agent metadata from sessions
- [Session Hierarchy](./session-hierarchy.md) - Understanding session relationships
