---
title: ErkBot Agent Event System
read_when:
  - "working with erkbot agent streaming or events"
  - "modifying erkbot event types or stream processing"
  - "adding new agent event types to erkbot"
tripwires:
  - action: "using attribute access on Claude SDK message objects in erkbot"
    warning: "The Claude Agent SDK uses dict-access patterns (.get('key')), not attribute access. See stream.py for the correct pattern."
  - action: "adding a new event type without updating the AgentEvent union"
    warning: "AgentEvent is a Union type in events.py. New event types must be added to it, or they won't be matched in downstream event handlers."
---

# ErkBot Agent Event System

ErkBot wraps the Claude Agent SDK's streaming API into a typed event system using frozen dataclasses. This provides type-safe event handling for Slack integration.

## Event Types

<!-- Source: packages/erkbot/src/erkbot/agent/events.py, AgentEvent -->

Six frozen dataclass event types are defined in `events.py`:

- **`TextDelta`** — Incremental text content from the agent (field: `text`)
- **`ToolStart`** — A tool invocation has begun (fields: `tool_name`, `tool_use_id`)
- **`ToolEnd`** — A tool invocation has completed (fields: `tool_name`, `tool_use_id`)
- **`TurnStart`** — A new agent turn has started (field: `turn_index`)
- **`TurnEnd`** — An agent turn has completed (field: `turn_index`)
- **`AgentResult`** — Final result with metadata (fields: `session_id`, `num_turns`, `input_tokens`, `output_tokens`)

The `AgentEvent` type alias is a discriminated union of all six types, enabling exhaustive `isinstance()` matching in event handlers.

## Stream Converter

<!-- Source: packages/erkbot/src/erkbot/agent/stream.py, stream_agent_events -->

`stream_agent_events()` is an async generator that converts raw Claude SDK messages into typed `AgentEvent` instances. It maintains state via:

- **`turn_index`** — Tracks which turn the agent is on (incremented on each `AssistantMessage`). `TurnStart` is emitted when a `message_start` `StreamEvent` is received.
- **`active_tool`** — Tracks the currently executing tool as a frozen dataclass with `tool_name` and `tool_use_id`
- **`turn_started`** — Boolean flag ensuring `TurnStart` is emitted exactly once per turn

The converter handles four SDK message types: `StreamEvent` (text deltas, tool use), `AssistantMessage` (turn boundaries), `ResultMessage` (final result), and `SystemMessage` (ignored).

### Tool Generation vs Tool Execution

Tool lifecycle events distinguish two phases:

1. **Tool generation** — The SDK streams a `content_block_start` with `type: "tool_use"`, yielding `ToolStart`
2. **Tool completion** — When a `content_block_stop` event is received, the converter emits `ToolEnd` if an active tool block exists, then clears the active tool state

## Helper Utilities

<!-- Source: packages/erkbot/src/erkbot/agent/helpers.py -->

Three high-level functions process event streams:

- **`accumulate_text()`** — Collects all `TextDelta` events into a final concatenated string
- **`collect_events()`** — Buffers all events from an async iterator into a list
- **`extract_result()`** — Searches backwards through an event list for the `AgentResult` (returns `None` if not found)

## Related Documentation

- [ErkBot Architecture](erkbot-architecture.md) — Overall erkbot design and Slack integration patterns
