---
title: Agent Type Extraction
read_when:
  - "extracting agent type from session"
  - "finding subagent_type for agent sessions"
  - "correlating agent sessions to their Task invocation"
  - "displaying agent metadata in session show"
---

# Agent Type Extraction

How to extract the agent type (e.g., "devrun", "Explore", "Plan") for agent sessions.

## Key Insight

The `subagent_type` is stored in the **parent session's** Task tool invocation, NOT in the agent session itself. The link between Task invocation and agent is via explicit metadata in `toolUseResult.agentId`.

## Deterministic Matching

Agent types are extracted using explicit ID linking (no timestamp correlation needed):

1. **Task tool_use**: `tool_use.id` → `subagent_type`
2. **tool_result entry**: `message.content[].tool_use_id` + `toolUseResult.agentId`
3. **Match**: `tool_use.id == tool_use_id` → `agent-{agentId}` → `subagent_type`

**Implementation:** See `extract_agent_types()` in `show_cmd.py`

## Data Structures

### Task tool_use (in parent session)

```json
{
  "type": "assistant",
  "message": {
    "content": [
      {
        "type": "tool_use",
        "id": "toolu_01MznpykDVuuWDomHNVBkALg",
        "name": "Task",
        "input": {
          "subagent_type": "devrun",
          "description": "Run tests"
        }
      }
    ]
  }
}
```

### tool_result with agentId (in parent session)

```json
{
  "type": "user",
  "message": {
    "content": [
      {
        "tool_use_id": "toolu_01MznpykDVuuWDomHNVBkALg",
        "type": "tool_result",
        "content": "Task completed"
      }
    ]
  },
  "toolUseResult": {
    "agentId": "a65aee7",
    "status": "completed"
  }
}
```

The `toolUseResult.agentId` is **explicit structured metadata** - no text parsing required.

## Common Agent Types

| `subagent_type`     | Description                                |
| ------------------- | ------------------------------------------ |
| `"Plan"`            | Planning agents for implementation design  |
| `"Explore"`         | Codebase exploration agents                |
| `"devrun"`          | Dev tool execution (pytest, pyright, etc.) |
| `"general-purpose"` | General multi-step task agents             |

## Edge Cases

- **Agent still running**: No `tool_result` yet → type cannot be determined
- **Agent crashed**: May have `tool_result` with error status but still has `agentId`
- **Non-Task agents**: "Warmup" agents don't have Task invocations → no type

## Implementation Reference

- **Extraction:** `src/erk/cli/commands/cc/session/show_cmd.py:extract_agent_types()`
