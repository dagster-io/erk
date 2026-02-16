---
title: Claude CLI Stream-JSON Format
read_when:
  - "parsing claude cli output"
  - "extracting metadata from stream-json"
  - "working with session_id"
  - "implementing stream-json parser"
last_audited: "2026-02-05 00:00 PT"
audit_result: edited
---

# Claude CLI Stream-JSON Format

## Overview

The Claude CLI's `--output-format stream-json` produces newline-delimited JSON (JSONL) where each line represents a discrete event in the conversation.

## Top-Level Structure

Every stream-json line is a JSON object:

```json
{
  "type": "assistant" | "user" | "system" | "result",
  "session_id": "abc123-def456",
  "message": {
    "role": "assistant" | "user",
    "content": [...]
  }
}
```

**Message types:**

| Type        | Description                                     |
| ----------- | ----------------------------------------------- |
| `assistant` | Claude's text responses and tool uses           |
| `user`      | Tool results returned to Claude                 |
| `system`    | Metadata and initialization events              |
| `result`    | Final result with `num_turns`, `is_error`, etc. |

## Common Pitfalls

### 1. Looking for session_id in the wrong place

**CRITICAL:** `session_id` is at the **top level**, NOT nested in `message`:

```python
# WRONG
session_id = data.get("message", {}).get("session_id")  # None

# CORRECT
session_id = data.get("session_id")  # "abc123-def456"
```

### 2. Assuming content is always a list

Tool result content can be a string OR a list:

```python
# WRONG
content = tool_result.get("content")[0]  # TypeError if string

# CORRECT
content = tool_result.get("content")
if isinstance(content, str):
    process_string(content)
elif isinstance(content, list):
    process_list(content)
```

### 3. Not handling JSON parse errors

```python
# Wrap in try/except for malformed lines
try:
    data = json.loads(line)
except json.JSONDecodeError:
    continue
```

## Implementation References

- `src/erk/core/prompt_executor.py` — `ClaudePromptExecutor._parse_stream_json_line()` handles all message types
- `src/erk/core/output_filter.py` — Text extraction and tool summarization functions

## Related Documentation

- [CommandResult Extension Pattern](../architecture/commandresult-extension-pattern.md) — Adding new metadata fields based on stream-json parsing
