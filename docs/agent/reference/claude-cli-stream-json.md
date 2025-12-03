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

### Basic Text Extraction

```python
import json

def extract_text_from_assistant(line: str) -> str | None:
    """Extract text content from assistant message."""
    data = json.loads(line)

    if data.get("type") != "assistant":
        return None

    message = data.get("message", {})
    content = message.get("content", [])

    text_parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text")
            if text:
                text_parts.append(text)

    return "\n".join(text_parts) if text_parts else None
```

### Session ID Extraction

```python
def extract_session_id(line: str) -> str | None:
    """Extract session_id from stream-json line."""
    data = json.loads(line)
    return data.get("session_id")
```

### Tool Use Detection

```python
def extract_tool_uses(line: str) -> list[dict]:
    """Extract tool use blocks from assistant message."""
    data = json.loads(line)

    if data.get("type") != "assistant":
        return []

    message = data.get("message", {})
    content = message.get("content", [])

    tools = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "tool_use":
            tools.append(item)

    return tools
```

### Tool Result Extraction

```python
def extract_tool_result_content(tool_result: dict) -> str | None:
    """Extract content from tool result, handling both string and list formats."""
    content = tool_result.get("content")

    # String format
    if isinstance(content, str):
        return content

    # List format - extract text from first text item
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                return item.get("text")

    return None
```

## Complete Streaming Parser Example

```python
import json
import subprocess
from pathlib import Path

def stream_claude_output(command: str, cwd: Path) -> None:
    """Execute Claude CLI and parse stream-json output."""
    cmd_args = [
        "claude",
        "--output-format", "stream-json",
        "--permission-mode", "acceptEdits",
        command
    ]

    process = subprocess.Popen(
        cmd_args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
    )

    session_id: str | None = None

    if process.stdout:
        for line in process.stdout:
            if not line.strip():
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Capture session_id (appears in every line)
            if session_id is None:
                session_id = data.get("session_id")
                if session_id:
                    print(f"Session ID: {session_id}")

            # Process assistant messages
            if data.get("type") == "assistant":
                message = data.get("message", {})
                content = message.get("content", [])

                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            print(f"Text: {item.get('text')}")
                        elif item.get("type") == "tool_use":
                            print(f"Tool: {item.get('name')}")

    process.wait()
```

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
