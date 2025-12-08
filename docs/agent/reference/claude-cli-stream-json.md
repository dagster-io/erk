---
title: Claude CLI Stream-JSON Format
read_when:
  - "parsing claude cli output"
  - "extracting metadata from stream-json"
  - "working with session_id"
  - "implementing stream-json parser"
---

# Claude CLI Stream-JSON Format

## Overview

The Claude CLI's `--output-format stream-json` produces newline-delimited JSON (JSONL) where each line represents a discrete event in the conversation. This format enables programmatic parsing of Claude's responses, tool uses, and metadata.

## Top-Level Structure

Every stream-json line is a JSON object with this structure:

```json
{
  "type": "assistant" | "user" | "system",
  "session_id": "abc123-def456",
  "message": {
    "role": "assistant" | "user",
    "content": [...]
  }
}
```

**Key fields:**

- **`type`**: Message type - `"assistant"` (Claude's responses), `"user"` (tool results), or `"system"` (metadata)
- **`session_id`**: Session identifier appearing at the **top level** of each JSON object (not nested in `message`)
- **`message`**: Nested object containing `role` and `content` array

## Session ID Location

**CRITICAL:** `session_id` appears at the **top level** of each JSON object, NOT within the nested `message` object:

```python
# ✅ CORRECT - session_id at top level
data = json.loads(line)
session_id = data.get("session_id")  # "abc123-def456"

# ❌ WRONG - session_id is NOT in message
session_id = data.get("message", {}).get("session_id")  # None
```

## Message Types

### Assistant Messages (`type: "assistant"`)

Claude's text responses and tool uses. The `message.content` array contains text blocks and tool use blocks.

**Example with text:**

```json
{
  "type": "assistant",
  "session_id": "abc123-def456",
  "message": {
    "role": "assistant",
    "content": [
      {
        "type": "text",
        "text": "I'll help you implement that feature."
      }
    ]
  }
}
```

**Example with tool use:**

```json
{
  "type": "assistant",
  "session_id": "abc123-def456",
  "message": {
    "role": "assistant",
    "content": [
      {
        "type": "tool_use",
        "id": "toolu_123",
        "name": "Edit",
        "input": {
          "file_path": "/repo/src/file.py",
          "old_string": "old code",
          "new_string": "new code"
        }
      }
    ]
  }
}
```

### User Messages (`type: "user"`)

Tool results returned to Claude. The `message.content` array contains tool result blocks.

**Example:**

```json
{
  "type": "user",
  "session_id": "abc123-def456",
  "message": {
    "role": "user",
    "content": [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_123",
        "content": "Tool execution successful"
      }
    ]
  }
}
```

**Tool result content formats:**

Tool results can be either a string or a list:

```python
# String format (common for simple results)
{
  "type": "tool_result",
  "content": "Success"
}

# List format (for structured content)
{
  "type": "tool_result",
  "content": [
    {"type": "text", "text": "Result text here"}
  ]
}
```

### System Messages (`type: "system"`)

Metadata and initialization events. These are typically filtered out in production parsers.

## Parsing in Python

### Canonical Implementation

For parsing stream-json output, use the production implementation:

**Source**: `dot_agent_kit/data/kits/command/kit_cli_commands/command/message_parsing.py`

Functions available:

- `extract_text_from_assistant_message(msg)` - Extract text content from assistant message
- `extract_tool_uses_from_assistant_message(msg)` - Extract tool use blocks as `ToolUse` dataclass
- `extract_tool_results_from_user_message(msg)` - Extract tool results as `ToolResult` dataclass

### Session ID Extraction

Session ID is at the **top level** of the parsed JSON:

```python
data = json.loads(line)
session_id = data.get("session_id")  # Top level, not nested in message
```

### Key Patterns

- **Parse each line as JSON**: `data = json.loads(line)`
- **Check message type**: `data.get("type")` returns `"assistant"`, `"user"`, or `"system"`
- **Access content array**: `data.get("message", {}).get("content", [])`
- **Handle tool result formats**: Content can be string OR list - check with `isinstance()`
- **Handle parse errors**: Wrap `json.loads()` in try/except for malformed lines

## Common Pitfalls

### 1. Looking for session_id in the wrong place

```python
# ❌ WRONG - session_id is NOT nested in message
data = json.loads(line)
session_id = data.get("message", {}).get("session_id")  # None

# ✅ CORRECT - session_id is at top level
session_id = data.get("session_id")  # "abc123-def456"
```

### 2. Assuming content is always a list

```python
# ❌ WRONG - content might be a string
content = tool_result.get("content")[0]  # TypeError if string

# ✅ CORRECT - check type first
content = tool_result.get("content")
if isinstance(content, str):
    process_string(content)
elif isinstance(content, list):
    process_list(content)
```

### 3. Not handling JSON parse errors

```python
# ❌ WRONG - crash on malformed JSON
data = json.loads(line)

# ✅ CORRECT - handle parse errors
try:
    data = json.loads(line)
except json.JSONDecodeError:
    continue  # Skip malformed lines
```

## Related

- **CommandResult Extension Pattern**: [commandresult-extension-pattern.md](../architecture/commandresult-extension-pattern.md) - How to add new metadata fields based on stream-json parsing
- **Implementation Reference**: `src/erk/core/claude_executor.py` - RealClaudeExecutor.\_parse_stream_json_line()
- **Output Filtering**: `src/erk/core/output_filter.py` - Text extraction and tool summarization functions
