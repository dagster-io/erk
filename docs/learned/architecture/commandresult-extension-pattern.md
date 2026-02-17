---
title: CommandResult Extension Pattern
read_when:
  - "adding new field to CommandResult"
  - "extending CommandResult dataclass"
  - "adding metadata extraction"
  - "implementing new CommandResult field"
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
---

# CommandResult Extension Pattern

## Overview

Step-by-step checklist for adding new metadata fields to `CommandResult`. The pattern ensures metadata flows correctly through the parsing pipeline, the typed event system, the streaming executor, the non-streaming wrapper, streaming consumers, the fake executor, and tests.

## When to Use This Pattern

- Extract new metadata from Claude CLI's stream-json output
- Add tracking for new PR/issue attributes
- Capture execution metadata not currently in CommandResult

## Architecture Context

The executor pipeline has these key locations (read each before making changes):

| Component                     | Location                                                     | Role                                                                                                                                                                 |
| ----------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ABC + types + `CommandResult` | `packages/erk-shared/src/erk_shared/core/prompt_executor.py` | Defines `CommandResult`, typed event dataclasses (`TextEvent`, `PrUrlEvent`, etc.), `ExecutorEvent` union, and `PromptExecutor` ABC with default `execute_command()` |
| Real executor                 | `src/erk/core/prompt_executor.py`                            | `ClaudePromptExecutor` — implements `execute_command_streaming()` and `_parse_stream_json_line()`                                                                    |
| Streaming consumer            | `src/erk/cli/output.py`                                      | `stream_command_with_feedback()` — consumes `ExecutorEvent` stream with live UI                                                                                      |
| Fake executor                 | `tests/fakes/prompt_executor.py`                             | `FakePromptExecutor` — test double with `simulated_*` constructor params                                                                                             |

**Key design detail:** The system uses **typed frozen dataclass events** (e.g., `PrUrlEvent(url=...)`, `TextEvent(content=...)`), NOT a generic `StreamEvent` class. Each event type is a separate `@dataclass(frozen=True)` class. See `ExecutorEvent` union type in the ABC module. All streaming methods use keyword-only arguments (`*,`).

## Complete Checklist

Follow these 8 steps in order:

### 1. Add Field to `CommandResult`

**File:** `packages/erk-shared/src/erk_shared/core/prompt_executor.py`

Add the new field to the frozen dataclass. Place it with related fields (e.g., PR fields together). Use `str | None` for optional string metadata.

See existing fields at `packages/erk-shared/src/erk_shared/core/prompt_executor.py:133`.

### 2. Create a Typed Event Dataclass

**File:** `packages/erk-shared/src/erk_shared/core/prompt_executor.py`

Create a new frozen dataclass event (following the pattern of `PrUrlEvent`, `IssueNumberEvent`, etc.) and add it to the `ExecutorEvent` union type.

### 3. Add Key to `_parse_stream_json_line()` Result Dict

**File:** `src/erk/core/prompt_executor.py`

Initialize the new key as `None` in the result dict at `ClaudePromptExecutor._parse_stream_json_line()`.

### 4. Add Extraction Logic in `_parse_stream_json_line()`

**File:** `src/erk/core/prompt_executor.py`

Add logic to extract the field from parsed JSON data.

**CRITICAL:** Understand where data appears in stream-json structure:

- **Top-level fields**: `data.get("field_name")`
- **Message content** (text): `data.get("message", {}).get("content", [])`
- **Tool results** (PR metadata): Check `type: "user"` messages with `tool_result` content

See [claude-cli-stream-json.md](../reference/claude-cli-stream-json.md) for complete format reference.

### 5. Yield Typed Event in `execute_command_streaming()`

**File:** `src/erk/core/prompt_executor.py`

After parsing, check for the new key and yield the typed event:

```python
# Pattern: check parsed dict, yield typed event
new_value = parsed.get("new_field")
if new_value is not None:
    yield NewFieldEvent(field_name=str(new_value))
```

### 6. Add Match Case in `execute_command()`

**File:** `packages/erk-shared/src/erk_shared/core/prompt_executor.py`

The default `execute_command()` on the ABC uses `match`/`case` to collect events into `CommandResult`. Add a new case branch and pass the captured value to the `CommandResult` constructor.

See the existing match block at `packages/erk-shared/src/erk_shared/core/prompt_executor.py:276`.

### 7. Update Streaming Consumers

**File:** `src/erk/cli/output.py` (and any other `execute_command_streaming()` consumers)

Add handling for the new event type in `stream_command_with_feedback()` and any other code that iterates over `ExecutorEvent`.

### 8. Update `FakePromptExecutor`

**File:** `tests/fakes/prompt_executor.py`

Add a `simulated_*` keyword-only constructor parameter and yield the corresponding typed event in `execute_command_streaming()`. Update `execute_command()` to include the field in the returned `CommandResult`.

Then add tests for:

- **Parsing**: `_parse_stream_json_line()` extracts the field correctly
- **Fake simulation**: `FakePromptExecutor` yields the event
- **Integration**: `execute_command()` captures the event into `CommandResult`

## Common Pitfalls

### 1. Forgetting to initialize in result dict

If a new key isn't added to the result dict in `_parse_stream_json_line()`, later assignment will work (dicts accept new keys) but the key won't exist when checked with `.get()` in `execute_command_streaming()` — leading to silently missing events.

### 2. Not yielding the event in execute_command_streaming

Parsing the field but forgetting to yield a typed event means `execute_command()` never captures it. The data is extracted and discarded.

### 3. Extracting from wrong location in JSON

Stream-json has different nesting levels. PR metadata lives inside `type: "user"` messages under `tool_result` content, while fields like `num_turns` are at the top level of `type: "result"` messages. Always verify the JSON path against the stream-json reference doc.

### 4. Not updating FakePromptExecutor

Without a `simulated_*` parameter on the fake, tests cannot verify the new field's behavior through the full pipeline.

### 5. Forgetting the ExecutorEvent union

If the new event dataclass isn't added to the `ExecutorEvent` union type, type checkers won't require match/case branches for it, and consumers may silently ignore it.

## Related

- **Stream-JSON Format**: [claude-cli-stream-json.md](../reference/claude-cli-stream-json.md)
- **ABC + Types**: `packages/erk-shared/src/erk_shared/core/prompt_executor.py`
- **Real Executor**: `src/erk/core/prompt_executor.py`
- **Fake Executor**: `tests/fakes/prompt_executor.py`
- **Streaming Consumer**: `src/erk/cli/output.py`
