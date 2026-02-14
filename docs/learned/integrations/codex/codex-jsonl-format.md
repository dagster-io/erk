---
title: Codex CLI JSONL Output Format
read_when:
  - "parsing codex exec --json output"
  - "implementing a CodexPromptExecutor"
  - "mapping Codex events to erk ExecutorEvent types"
  - "comparing Claude stream-json and Codex JSONL formats"
tripwires:
  - action: "assuming Codex JSONL uses same format as Claude stream-json"
    warning: "Completely different formats. Claude uses type: assistant/user/result with nested message.content[]. Codex uses type: thread.started/turn.*/item.* with flattened item fields. See this document."
  - action: "looking for session_id in Codex JSONL events"
    warning: "Codex JSONL does not include session_id in events. The thread_id is provided in the thread.started event only — you must capture it from that first event and carry it forward."
  - action: "parsing item fields as nested objects"
    warning: "Codex uses Rust #[serde(flatten)] — item type-specific fields appear as siblings of id and type within the item object, not in a nested sub-object."
  - action: "reusing ClaudePromptExecutor parsing logic for Codex"
    warning: "The two formats share almost nothing structurally. A CodexPromptExecutor needs its own parser — don't parameterize the existing Claude parser."
last_audited: "2026-02-08 13:55 PT"
audit_result: clean
---

# Codex CLI JSONL Output Format

Reverse-engineered reference for the JSONL event stream produced by `codex exec --json`. Verified against the Codex open-source Rust repository (https://github.com/openai/codex), specifically `codex-rs/exec/src/exec_events.rs`. Research date: February 2, 2026.

This document exists because OpenAI provides **no documentation** for this format. It was reverse-engineered from Rust source code, and losing this research would cost significant time to redo. The format is a third-party API specification — code examples below show data shapes, not erk implementation.

## Why a Separate Parser Is Required

<!-- Source: packages/erk-shared/src/erk_shared/core/prompt_executor.py, PromptExecutor -->
<!-- Source: src/erk/core/prompt_executor.py, ClaudePromptExecutor._parse_stream_json_line -->

Erk's `PromptExecutor` ABC abstracts streaming execution behind `Iterator[ExecutorEvent]`. See `PromptExecutor` in `packages/erk-shared/src/erk_shared/core/prompt_executor.py` for the ABC, and `ClaudePromptExecutor._parse_stream_json_line()` in `src/erk/core/prompt_executor.py` for the Claude implementation.

The natural instinct is to parameterize the existing Claude parser for Codex. This won't work — the formats share almost nothing structurally. Claude uses a single-level `type` field (`assistant`/`user`/`result`) with content nested in `message.content[]` blocks. Codex uses a completely different two-level type system with flattened item fields. A `CodexPromptExecutor` needs its own `_parse_jsonl_line()` method built from the format spec below.

## Two-Level Type Discrimination

The core design decision in Codex's format is a **two-level type system**: every JSONL line has a top-level `type` field for the event lifecycle stage, and item events contain a nested `item.type` for the content kind.

Codex uses Rust's `#[serde(flatten)]` on item details. This means type-specific fields appear as **siblings** of `id` and `type` within the `item` object — not nested inside a content sub-object:

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

**Why this matters for parsing:** You cannot write a generic "extract content from item" function. Each `item.type` has different sibling fields, so you must dispatch on `item.type` first. The parsing pattern is: `match (event["type"], event["item"]["type"])`.

## Event Type Reference

### Top-Level Events

| Event Type       | When Emitted                | Key Fields                                                 |
| ---------------- | --------------------------- | ---------------------------------------------------------- |
| `thread.started` | Always first event          | `thread_id` (string, UUID) — only source of session ID     |
| `turn.started`   | User prompt sent to model   | (empty object)                                             |
| `turn.completed` | Turn finished successfully  | `usage.{input_tokens, cached_input_tokens, output_tokens}` |
| `turn.failed`    | Turn ended with error       | `error.message`                                            |
| `item.started`   | New item begun              | `item.id`, `item.{type-specific fields}`                   |
| `item.updated`   | Item status update          | `item.id`, `item.{type-specific fields}`                   |
| `item.completed` | Item reached terminal state | `item.id`, `item.{type-specific fields}`                   |
| `error`          | Unrecoverable stream error  | `message`                                                  |

### Item Types (Second-Level)

| Item Type           | Purpose                   | Key Fields                                                  |
| ------------------- | ------------------------- | ----------------------------------------------------------- |
| `agent_message`     | Agent text response       | `text`                                                      |
| `reasoning`         | Agent reasoning summary   | `text`                                                      |
| `command_execution` | Shell command execution   | `command`, `aggregated_output`, `exit_code`, `status`       |
| `file_change`       | File modifications        | `changes[].{path, kind}`, `status`                          |
| `mcp_tool_call`     | MCP tool invocation       | `server`, `tool`, `arguments`, `result`, `error`, `status`  |
| `collab_tool_call`  | Multi-agent collaboration | `tool`, `sender_thread_id`, `receiver_thread_ids`, `status` |
| `web_search`        | Web search request        | `id`, `query`, `action`                                     |
| `todo_list`         | Agent's to-do list        | `items[].{text, completed}`                                 |
| `error`             | Non-fatal error           | `message`                                                   |

### Status Enums

Valid values for `status` fields across item types:

- **CommandExecutionStatus**: `in_progress`, `completed`, `failed`, `declined`
- **PatchApplyStatus** (file_change): `in_progress`, `completed`, `failed`
- **PatchChangeKind** (file_change changes[].kind): `add`, `delete`, `update`
- **McpToolCallStatus**: `in_progress`, `completed`, `failed`
- **CollabToolCallStatus**: `in_progress`, `completed`, `failed`
- **CollabAgentStatus**: `pending_init`, `running`, `completed`, `errored`, `shutdown`, `not_found`
- **CollabTool**: `spawn_agent`, `send_input`, `wait`, `close_agent`

## Representative JSON Examples

Top-level events are simple objects. `thread.started` carries the session identifier:

```json
{
  "type": "thread.started",
  "thread_id": "67e55044-10b1-426f-9247-bb680e5fe0c8"
}
```

`turn.completed` carries token usage:

```json
{
  "type": "turn.completed",
  "usage": {
    "input_tokens": 1200,
    "cached_input_tokens": 200,
    "output_tokens": 345
  }
}
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

## Structural Differences from Claude

These differences explain why a `CodexPromptExecutor` needs entirely separate parsing logic:

| Aspect                | Claude stream-json                            | Codex --json                                  | Implication                                                                      |
| --------------------- | --------------------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------- |
| Top-level type values | `assistant`, `user`, `result`                 | `thread.started`, `turn.*`, `item.*`, `error` | Completely different dispatch trees                                              |
| Message nesting       | `message.content[]` array with typed blocks   | Flat item fields via `#[serde(flatten)]`      | Content extraction logic is incompatible                                         |
| Tool use reporting    | `tool_use` blocks in `assistant` messages     | `command_execution` and `file_change` items   | Claude bundles tool use and text; Codex separates them as distinct items         |
| Tool results          | `tool_result` blocks in `user` messages       | Folded into `item.completed` fields           | Claude reports results in a separate event; Codex merges them into the item      |
| Session ID            | `session_id` at top level of every event      | `thread_id` in `thread.started` only          | Must capture thread_id from first event and carry it forward                     |
| Completion signal     | `type: "result"` with `num_turns`, `is_error` | `turn.completed` with `usage`                 | No equivalent to Claude's `num_turns=0` hook-blocking detection                  |
| Error reporting       | Non-zero exit code + stderr                   | `turn.failed` or `error` events               | Codex reports errors in-band; Claude requires checking both exit code and stderr |

### The `num_turns` Gap

Claude's `type: "result"` event includes `num_turns`, which erk uses to detect hook blocking (emitted as `NoTurnsEvent`). Codex has no equivalent field. A future `CodexPromptExecutor` would need a different strategy for hook-blocking detection — for example, checking whether any `item.*` events appeared between `turn.started` and `turn.completed`. Without this, `NoTurnsEvent` and `NoOutputEvent` diagnostics cannot be ported directly.

## Planned Event-to-ExecutorEvent Mapping

<!-- Source: packages/erk-shared/src/erk_shared/core/prompt_executor.py, ExecutorEvent -->

No `CodexPromptExecutor` exists yet. This table captures the intended mapping from Codex events to erk's `ExecutorEvent` union (see `ExecutorEvent` in `packages/erk-shared/src/erk_shared/core/prompt_executor.py`).

| Codex Event                            | Erk ExecutorEvent    | Rationale                                                    |
| -------------------------------------- | -------------------- | ------------------------------------------------------------ |
| `item.completed` + `agent_message`     | `TextEvent`          | Direct mapping — extract `text` field                        |
| `item.started` + `command_execution`   | `SpinnerUpdateEvent` | Shows in-progress command name while executing               |
| `item.completed` + `command_execution` | `ToolEvent`          | Summarize command + output + exit code                       |
| `item.completed` + `file_change`       | `ToolEvent`          | Summarize file changes                                       |
| `item.started` + `mcp_tool_call`       | `SpinnerUpdateEvent` | Shows tool name during invocation                            |
| `item.completed` + `mcp_tool_call`     | `ToolEvent`          | Summarize tool result or error                               |
| `turn.failed`                          | `ErrorEvent`         | Extract `error.message`                                      |
| `error`                                | `ErrorEvent`         | Extract `message`                                            |
| PR URLs in `agent_message` text        | `PrUrlEvent` etc.    | Reuse existing text-based PR metadata extraction             |
| `thread.started`                       | (capture only)       | Store `thread_id` for logging; don't emit to event consumers |
| `turn.started`                         | (ignored)            | No useful information for erk's event consumers              |
| `turn.completed`                       | (ignored)            | Usage tracking only — may want to log tokens                 |
| `item.started/updated` + `todo_list`   | `SpinnerUpdateEvent` | Optional — could show agent progress                         |
| `item.completed` + `reasoning`         | (ignored)            | No erk consumer for reasoning summaries yet                  |

**Open design question:** How to detect hook blocking without `num_turns`. `NoTurnsEvent` and `NoOutputEvent` depend on Claude's `type: "result"` event, which has no Codex equivalent.

## Related Documentation

- [Codex CLI Reference](codex-cli-reference.md) — CLI flags, sandbox modes, and feature gaps that constrain executor porting
- [Claude CLI Stream-JSON Format](../../reference/claude-cli-stream-json.md) — Claude's equivalent format and common parsing pitfalls
- [Prompt Executor Gateway](../../architecture/prompt-executor-gateway.md) — The ABC, execution modes, and fake implementation patterns
