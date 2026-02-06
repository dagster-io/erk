---
title: Codex CLI JSONL Output Format
read_when:
  - "parsing codex exec --json output"
  - "implementing a Codex PromptExecutor"
  - "mapping Codex events to ExecutorEvent types"
  - "comparing Claude and Codex streaming formats"
tripwires:
  - action: "assuming Codex JSONL uses same format as Claude stream-json"
    warning: "Completely different formats. Claude uses type: assistant/user/result with nested message.content[]. Codex uses type: item.completed with flattened item fields. See codex-jsonl-format.md."
  - action: "looking for session_id in Codex JSONL"
    warning: "Codex JSONL does not include session_id in events. The thread_id is provided in the thread.started event only."
last_audited: "2026-02-05 20:38 PT"
audit_result: edited
---

# Codex CLI JSONL Output Format

Reference for the JSONL event stream produced by `codex exec --json`. Verified against source code in `codex-rs/exec/src/exec_events.rs`.

## Overview

When `--json` is passed to `codex exec`, each line of stdout is a JSON object representing one event. Events use a two-level type discrimination system.

## Top-Level Event Types

Every JSONL line has a `type` field identifying the event kind:

| Event Type       | Description                                 | Key Fields                                                 |
| ---------------- | ------------------------------------------- | ---------------------------------------------------------- |
| `thread.started` | Session initialization (always first event) | `thread_id` (string, UUID)                                 |
| `turn.started`   | User prompt sent to model                   | (empty object)                                             |
| `turn.completed` | Turn finished successfully                  | `usage.{input_tokens, cached_input_tokens, output_tokens}` |
| `turn.failed`    | Turn ended with error                       | `error.message`                                            |
| `item.started`   | New item begun (in progress)                | `item.id`, `item.{type-specific fields}`                   |
| `item.updated`   | Item status update                          | `item.id`, `item.{type-specific fields}`                   |
| `item.completed` | Item reached terminal state                 | `item.id`, `item.{type-specific fields}`                   |
| `error`          | Unrecoverable stream error                  | `message`                                                  |

## Item Types (Second-Level Discrimination)

Item events (`item.started`, `item.updated`, `item.completed`) contain an `item` object with an `id` field and a flattened `type` field identifying the item kind:

| Item Type           | Description                  | Key Fields                                                  |
| ------------------- | ---------------------------- | ----------------------------------------------------------- |
| `agent_message`     | Agent text response          | `text`                                                      |
| `reasoning`         | Agent reasoning summary      | `text`                                                      |
| `command_execution` | Shell command execution      | `command`, `aggregated_output`, `exit_code`, `status`       |
| `file_change`       | File modifications           | `changes[].{path, kind}`, `status`                          |
| `mcp_tool_call`     | MCP tool invocation          | `server`, `tool`, `arguments`, `result`, `error`, `status`  |
| `collab_tool_call`  | Multi-agent collaboration    | `tool`, `sender_thread_id`, `receiver_thread_ids`, `status` |
| `web_search`        | Web search request           | `id`, `query`, `action`                                     |
| `todo_list`         | Agent's to-do list           | `items[].{text, completed}`                                 |
| `error`             | Non-fatal error notification | `message`                                                   |

## Two-Level Type Flattening

Codex uses Rust's `#[serde(flatten)]` on the item details, so both the item `id` and the type-specific fields appear at the same level in the JSON. This means an `item.completed` event for a command execution looks like:

```json
{
  "type": "item.completed",
  "item": {
    "id": "item_0",
    "type": "command_execution",
    "command": "bash -lc 'echo hi'",
    "aggregated_output": "hi\n",
    "exit_code": 0,
    "status": "completed"
  }
}
```

Note: `item.type` is the item kind discriminator, while the top-level `type` is the event kind. Both are present in the same JSON object but at different nesting levels.

## Status Enums

### CommandExecutionStatus

`in_progress`, `completed`, `failed`, `declined`

### PatchApplyStatus (file_change)

`in_progress`, `completed`, `failed`

### PatchChangeKind (file_change changes)

`add`, `delete`, `update`

### McpToolCallStatus

`in_progress`, `completed`, `failed`

### CollabToolCallStatus

`in_progress`, `completed`, `failed`

### CollabAgentStatus

`pending_init`, `running`, `completed`, `errored`, `shutdown`, `not_found`

### CollabTool

`spawn_agent`, `send_input`, `wait`, `close_agent`

## Representative JSON Examples

Top-level events are simple objects. `thread.started` carries the session identifier:

```json
{ "type": "thread.started", "thread_id": "67e55044-10b1-426f-9247-bb680e5fe0c8" }
```

`turn.completed` carries token usage:

```json
{ "type": "turn.completed", "usage": { "input_tokens": 1200, "cached_input_tokens": 200, "output_tokens": 345 } }
```

Item events show the two-level type discrimination. A `command_execution` progresses from `item.started` (with `status: "in_progress"`, `exit_code: null`) to `item.completed` (with `status: "completed"`, populated `exit_code` and `aggregated_output`):

```json
{
  "type": "item.completed",
  "item": {
    "id": "item_0",
    "type": "command_execution",
    "command": "bash -lc 'echo hi'",
    "aggregated_output": "hi\n",
    "exit_code": 0,
    "status": "completed"
  }
}
```

Other item types follow the same envelope pattern. The `item.type` field changes (e.g., `agent_message`, `file_change`, `mcp_tool_call`, `todo_list`) and the sibling fields vary per the Item Types table above. Error variants use `turn.failed` with `error.message` or top-level `{ "type": "error", "message": "..." }`.

## Key Structural Differences from Claude

| Aspect                | Claude stream-json                            | Codex --json                                  |
| --------------------- | --------------------------------------------- | --------------------------------------------- |
| Top-level type values | `assistant`, `user`, `result`                 | `thread.started`, `turn.*`, `item.*`, `error` |
| Message nesting       | `message.content[]` array with typed blocks   | Flat item fields via `#[serde(flatten)]`      |
| Tool use reporting    | `tool_use` blocks in `assistant` messages     | `command_execution` and `file_change` items   |
| Tool results          | `tool_result` blocks in `user` messages       | Included in `item.completed` fields           |
| Session ID            | `session_id` at top level of every event      | `thread_id` in `thread.started` only          |
| Completion signal     | `type: "result"` with `num_turns`, `is_error` | `turn.completed` with `usage`                 |
| Error reporting       | Non-zero exit code + stderr                   | `turn.failed` or `error` events               |

## Planned Event-to-ExecutorEvent Mapping for Erk

No `CodexPromptExecutor` exists yet. When one is built, it should map Codex events to erk's `ExecutorEvent` union (defined in `erk_shared.core.prompt_executor`):

| Codex Event                            | Erk ExecutorEvent                             |
| -------------------------------------- | --------------------------------------------- |
| `item.completed` + `agent_message`     | `TextEvent(content=text)`                     |
| `item.started` + `command_execution`   | `SpinnerUpdateEvent(status=command)`          |
| `item.completed` + `command_execution` | `ToolEvent(summary=...)`                      |
| `item.completed` + `file_change`       | `ToolEvent(summary=...)`                      |
| `item.started` + `mcp_tool_call`       | `SpinnerUpdateEvent(status=tool)`             |
| `item.completed` + `mcp_tool_call`     | `ToolEvent(summary=...)`                      |
| `turn.failed`                          | `ErrorEvent(message=...)`                     |
| `error`                                | `ErrorEvent(message=...)`                     |
| PR URLs found in `agent_message` text  | `PrUrlEvent`, `PrNumberEvent`, `PrTitleEvent` |
| `thread.started`                       | (ignored — extract thread_id for logging)     |
| `turn.started`                         | (ignored)                                     |
| `turn.completed`                       | (ignored — usage tracking only)               |
| `item.started/updated` + `todo_list`   | `SpinnerUpdateEvent` (optional)               |
| `item.completed` + `reasoning`         | (ignored or logged)                           |

## Related Documentation

- [Codex CLI Reference](codex-cli-reference.md) — CLI flags and sandbox modes
- [Claude CLI Stream-JSON Format](../reference/claude-cli-stream-json.md) — Claude's equivalent format
- [PromptExecutor Patterns](../architecture/prompt-executor-patterns.md) — How erk abstracts streaming
