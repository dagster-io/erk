---
title: Codex Integration
read_when:
  - "working with Codex executor or JSONL parsing"
  - "modifying permission mode mappings"
  - "adding new Codex event types or executor events"
  - "understanding how erk integrates with OpenAI Codex"
tripwires:
  - action: "adding a new Codex event type without updating the parser"
    warning: "All Codex event types must be handled in parse_codex_jsonl_line(). See codex-integration.md."
---

# Codex Integration

Erk integrates with OpenAI Codex as an alternative prompt executor. This covers the JSONL parser, permission mapping, and event model.

## CodexPromptExecutor

Factory-selected executor created via `create_prompt_executor()` in context initialization. Handles Codex-specific execution and output parsing.

## JSONL Parser

Standalone parser at `src/erk/core/codex_output_parser.py`.

### CodexParserState

Mutable class (not a dataclass) — intentional deviation from the frozen-dataclass convention. Parser state machines need mutable state passed by reference across `parse_codex_jsonl_line()` calls.

Fields:

- `thread_id: str | None` — current thread identifier
- `saw_any_items: bool` — tracks if any items were processed
- `saw_any_text: bool` — tracks if any text output was seen
- `_item_commands: dict[str, str]` — maps item IDs to commands

### Event Handling

`parse_codex_jsonl_line()` handles these event types:

| Event Type       | Handler                   | Description                |
| ---------------- | ------------------------- | -------------------------- |
| `thread.started` | `_handle_thread_started`  | New thread begins          |
| `item.started`   | `_handle_item_started`    | New item begins processing |
| `item.completed` | `_handle_item_completed`  | Item finished              |
| `turn.failed`    | `_handle_turn_failed`     | Turn error                 |
| `turn.completed` | `_handle_turn_completed`  | Turn finished              |
| `error`          | `_handle_top_level_error` | Top-level error            |

Ignored events: `turn.started`, `item.updated`.

Events are converted to erk's unified `ExecutorEvent` types for consistent handling across backends.

## Permission Mode Mapping

Defined in `packages/erk-shared/src/erk_shared/context/types.py`.

Erk defines four generic permission modes mapped to both Claude and Codex flags:

<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, PermissionMode -->

See `PermissionMode` in `packages/erk-shared/src/erk_shared/context/types.py`.

### Exec Mode (Headless)

`permission_mode_to_codex_exec()` — approval is hardcoded to Never, only sandbox flags matter:

| Permission  | Codex Flags           |
| ----------- | --------------------- |
| `safe`      | `--sandbox read-only` |
| `edits`     | `--full-auto`         |
| `plan`      | `--sandbox read-only` |
| `dangerous` | `--yolo`              |

### TUI Mode (Interactive)

`permission_mode_to_codex_tui()` — both sandbox and approval flags needed:

| Permission  | Codex Flags                               |
| ----------- | ----------------------------------------- |
| `safe`      | `--sandbox read-only -a untrusted`        |
| `edits`     | `--sandbox workspace-write -a on-request` |
| `plan`      | `--sandbox read-only -a never`            |
| `dangerous` | `--yolo`                                  |

Both functions use LBYL dictionary lookup with explicit `ValueError` on unknown modes.

## Related Topics

- [Codex CLI Reference](codex/codex-cli-reference.md) - Detailed CLI flag documentation
