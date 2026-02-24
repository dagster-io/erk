# Documentation Plan: Agent event loop module foundation (Objective #8036, Node 1.2)

## Context

This PR (#8070) establishes foundational agent event infrastructure for the erkbot package, implementing Claude Agent SDK streaming integration. The work creates a transport-neutral event system with 6 frozen dataclass event types, an async stream converter that transforms SDK messages into typed events, and helper utilities for event collection and text accumulation. This is the first agent/LLM code in erkbot (previously a CLI subprocess runner) and lays the foundation for downstream Slack bot integration.

Documentation is critical because this event system is **foundational infrastructure** for Objective #8036 (Ship Demo-Ready Agent-Mode erk-slack-bot). All downstream bot features (nodes 1.3-1.5) will consume these events. The patterns established here - discriminated unions, frozen dataclasses, state machine stream conversion - match existing erk conventions but are applied to a new domain (SDK integration vs CLI automation). Future agents working on erkbot need clear guidance on event semantics, extension patterns, and SDK integration gotchas.

The implementation discovered important non-obvious gotchas: the Claude Agent SDK's `StreamEvent.event` is a raw `dict[str, Any]`, not typed attributes, requiring `.get("key")` access patterns. Additionally, workspace package dependency management with `uv` requires package-specific sync commands when root sync doesn't detect changes. These warrant tripwires to prevent future developers from repeating the discovery process.

## Raw Materials

PR #8070

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 10    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score 2-3)| 2     |

## Stale Documentation Cleanup

No stale documentation detected. All existing docs with file references were verified clean.

## Documentation Items

### HIGH Priority

#### 1. Agent Event System Overview

**Location:** `docs/learned/integrations/erkbot/agent-event-system.md`
**Action:** CREATE
**Source:** [Impl] [PR #8070]

**Draft Content:**

```markdown
---
title: Erkbot Agent Event System
read_when:
  - working on erkbot agent integration
  - adding new event types to AgentEvent union
  - integrating Claude Agent SDK with streaming
  - understanding erkbot's event-driven architecture
tripwires:
  - action: "adding a new event type to AgentEvent union"
    warning: "Must update 3 places: events.py (add dataclass + union member), stream.py (handle in state machine), tests (add coverage). See extension checklist below."
    doc: "docs/learned/integrations/erkbot/agent-event-system.md"
---

# Erkbot Agent Event System

Overview of the transport-neutral event system for Claude Agent SDK integration.

## Event Types

Six frozen dataclass event types form a discriminated union:

- **TextDelta**: Streaming text content from assistant responses
- **ToolStart**: Tool generation begins (tool call being formed, NOT execution)
- **ToolEnd**: Tool generation completes (content_block_stop, NOT tool result)
- **TurnStart**: Multi-turn conversation lifecycle start
- **TurnEnd**: Multi-turn conversation lifecycle end
- **AgentResult**: Final result with session metadata and token counts

See `packages/erkbot/src/erkbot/agent/events.py` for type definitions (grep for `@dataclass(frozen=True)` and `AgentEvent =`).

## Design Decisions

### ToolEnd = "generated" not "executed"

The ToolEnd event fires when the model *finishes generating* a tool call (SDK's content_block_stop), not when the tool *executes*. Future nodes can add ToolResult for execution results.

### Token counts not USD

AgentResult provides integer token counts (input_tokens, output_tokens), not USD costs. Token counts are stable API values; USD depends on pricing and model which vary.

### No ErrorEvent

Exceptions propagate naturally from async generators. Adding an error event would require catching exceptions inside stream_agent_events() and break normal Python error handling. Callers wrap the async for loop in try/except.

### Frozen dataclasses

Matches erk convention (see ExecutorEvent in prompt_executor.py). Immutability prevents accidental mutation during async streaming.

## Extension Checklist

When adding a new event type:

1. Add frozen dataclass in events.py
2. Add to AgentEvent union type
3. Update stream_agent_events() state machine in stream.py
4. Add test coverage in test_agent_events.py and test_agent_stream.py

## Related Patterns

- ExecutorEvent union in `packages/erk-shared/src/erk_shared/core/prompt_executor.py` - same discriminated union pattern
- ProgressEvent/CompletionEvent in `packages/erk-shared/src/erk_shared/gateway/gt/events.py` - transport-neutral event precedent
- See prompt-executor-patterns.md for comparison (different abstraction but similar streaming approach)

## Research-First Integration Pattern

Before implementing SDK integrations, use Explore agent or WebFetch to fetch official SDK documentation. Do not assume based on training data - SDK types and behaviors may differ from expectations.
```

---

#### 2. Stream Converter State Machine

**Location:** `docs/learned/integrations/erkbot/agent-stream-converter.md`
**Action:** CREATE
**Source:** [Impl] [PR #8070]

**Draft Content:**

```markdown
---
title: Agent Stream Converter
read_when:
  - debugging event stream conversion
  - adding new event types to stream converter
  - understanding state machine for turn/tool tracking
  - troubleshooting missing or duplicate events
tripwires:
  - action: "modifying stream converter state machine"
    warning: "State machine has 3 pieces: turn_index (counter), active_tool (current tool block), turn_started (duplicate prevention). Changes affect event correlation."
    doc: "docs/learned/integrations/erkbot/agent-stream-converter.md"
---

# Agent Stream Converter

The `stream_agent_events()` async generator transforms Claude Agent SDK messages into typed AgentEvent instances.

## State Machine Architecture

Three pieces of state track event boundaries:

- **turn_index**: Counter incremented on each TurnEnd
- **active_tool**: Current _ActiveToolBlock or None (enables ToolEnd correlation)
- **turn_started**: Boolean preventing duplicate TurnStart within a turn

See `packages/erkbot/src/erkbot/agent/stream.py:30-82` for implementation (grep for `async def stream_agent_events`).

## SDK Event Mapping

**CRITICAL**: SDK's `StreamEvent.event` is `dict[str, Any]` - use `.get("key")` for access, NOT attribute access.

| SDK Event | Condition | AgentEvent | State Change |
|-----------|-----------|------------|--------------|
| message_start | turn_started=False | TurnStart | turn_started=True |
| content_block_start | type="tool_use" | ToolStart | active_tool set |
| content_block_delta | type="text_delta", text non-empty | TextDelta | none |
| content_block_stop | active_tool is not None | ToolEnd | active_tool cleared |
| AssistantMessage | - | TurnEnd | turn_index++, turn_started=False |
| ResultMessage | - | AgentResult | none |
| SystemMessage | - | (skip) | none |

## Internal State Tracking

The `_ActiveToolBlock` frozen dataclass stores tool_name and tool_use_id to emit correct ToolEnd events when content_block_stop fires.

See `packages/erkbot/src/erkbot/agent/stream.py:24-26` for definition.
```

---

#### 3. Claude Agent SDK Integration Tripwires

**Location:** `docs/learned/integrations/erkbot/tripwires.md`
**Action:** CREATE
**Source:** [Impl] [PR #8070]

**Draft Content:**

```markdown
---
title: Erkbot Integration Tripwires
read_when:
  - adding claude-agent-sdk to a new package
  - upgrading SDK version
  - debugging SDK event parsing issues
  - working on erkbot agent code
tripwires:
  - action: "adding claude-agent-sdk dependency"
    warning: "StreamEvent.event is dict[str, Any] - use .get('key') for access, NOT attribute access. Transitive deps include cffi 2.0.0 (large binary wheels)."
    doc: "docs/learned/integrations/erkbot/tripwires.md"
---

# Erkbot Integration Tripwires

Rules triggered by matching actions in erkbot code.

## Claude Agent SDK

**When**: Adding claude-agent-sdk dependency to any package

**Critical gotchas**:

- `StreamEvent.event` is a `dict[str, Any]` - use `.get("key")` for access, NOT attribute access
- SDK is transport-neutral but tightly coupled to Claude API streaming format
- Version constraint `>=0.1.0` is broad - pin tighter if stability issues arise
- Transitive dependencies include cffi 2.0.0 (large binary wheels)

**Source**: `packages/erkbot/pyproject.toml` (grep for `claude-agent-sdk`)
**Example**: `packages/erkbot/src/erkbot/agent/stream.py` demonstrates SDK integration with state machine converter

## AgentEvent Union Extension

**When**: Adding a new event type to AgentEvent union

**Required changes**:

1. Add frozen dataclass to events.py
2. Add to AgentEvent union type alias
3. Update stream_agent_events() state machine in stream.py
4. Add test coverage for new event type

**Source**: `packages/erkbot/src/erkbot/agent/events.py:39` (AgentEvent union)
```

---

#### 4. Workspace Package Dependency Sync Tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE (add new tripwire entry)
**Source:** [Impl]

**Draft Content:**

Add the following tripwire entry to the existing architecture/tripwires.md file:

```markdown
**running `uv sync` after adding dependencies to workspace packages** [pattern: `uv\s+sync(?!\s+--package)`] → Read [Workspace Package Dependency Management](TODO) first. Root `uv sync` may not detect changes in workspace package dependencies. Use `uv sync --package <package-name>` to force package-specific sync.
```

---

### MEDIUM Priority

#### 5. Helper Utilities Documentation

**Location:** `docs/learned/integrations/erkbot/agent-helpers.md`
**Action:** CREATE
**Source:** [PR #8070]

**Draft Content:**

```markdown
---
title: Agent Helper Utilities
read_when:
  - using helper utilities for event processing
  - writing tests that need to collect and assert on events
  - extracting final text or result from event stream
---

# Agent Helper Utilities

Three helper functions for consuming AgentEvent streams.

## Functions

### accumulate_text()

Consumes entire async stream, filters for TextDelta events, joins text parts into single string. Returns the accumulated text.

### collect_events()

Consumes entire async stream, returns all events as a list. Primarily used for tests that need to assert on event sequences.

### extract_result()

Searches backwards through collected events to find AgentResult. Returns None if no result present. Call after collect_events().

## Usage Patterns

**Important**: All three utilities consume the async stream completely - cannot be called on the same iterator twice.

- Use `accumulate_text()` when you only need the final text output
- Use `collect_events()` + `extract_result()` for post-processing and test assertions

See `packages/erkbot/src/erkbot/agent/helpers.py:6-25` for implementations.
```

---

#### 6. Testing Patterns for Erkbot Agent Code

**Location:** `docs/learned/testing/erkbot-agent-testing.md`
**Action:** CREATE
**Source:** [PR #8070]

**Draft Content:**

```markdown
---
title: Erkbot Agent Testing Patterns
read_when:
  - writing tests for erkbot agent code
  - testing async event streams
  - mocking Claude Agent SDK messages
---

# Erkbot Agent Testing Patterns

Test patterns for the erkbot agent module.

## Async Test Pattern

Use `unittest.IsolatedAsyncioTestCase` for async test methods:

```python
class TestStreamAgentEvents(IsolatedAsyncioTestCase):
    async def test_text_delta_events(self) -> None:
        ...
```

## Mock SDK Messages

Helper functions construct mock SDK messages:

- `_stream_event(dict)` - creates StreamEvent with dict payload
- `_async_iter(items)` - converts list to async iterator
- `_async_messages(items)` - creates async iterator of SDK Message types

## State Machine Test Coverage

Test stream converter with explicit coverage of:

- Turn lifecycle (TurnStart/TurnEnd boundaries)
- Tool lifecycle (ToolStart/ToolEnd correlation)
- Duplicate prevention (turn_started flag behavior)
- Edge cases (empty text, missing usage dict)

## Frozen Dataclass Testing

Verify immutability with `FrozenInstanceError` assertions:

```python
with self.assertRaises(FrozenInstanceError):
    event.text = "new value"
```

See test files in `packages/erkbot/tests/` for canonical patterns.
```

---

#### 7. PromptExecutor vs AgentEvent Distinction

**Location:** `docs/learned/architecture/prompt-executor-patterns.md`
**Action:** UPDATE (add section at end)
**Source:** [PR #8070]

**Draft Content:**

Add the following section at the end of the existing prompt-executor-patterns.md:

```markdown
## Related: erkbot AgentEvent System

The `erkbot` package has a **separate** event system for Claude Agent SDK streaming:

- **PromptExecutor** (erk core): Executes `claude` CLI binary, parses JSONL stdout into `ExecutorEvent` (ToolEvent, TextEvent, etc.)
- **AgentEvent** (erkbot): Wraps Claude Agent SDK `Message` stream, parses SDK dict events into `AgentEvent` (ToolStart, TextDelta, etc.)

**Key differences**:

| Aspect | PromptExecutor (erk core) | AgentEvent (erkbot) |
|--------|---------------------------|---------------------|
| Mechanism | Subprocess + JSONL parsing | SDK library + dict parsing |
| Events | ToolEvent, TextEvent, SuccessEvent, FailureEvent | ToolStart, ToolEnd, TextDelta, TurnStart, TurnEnd, AgentResult |
| Granularity | Command-level (PR URLs, success/failure) | Turn-level (token counts, session IDs) |
| Use case | CLI automation (erk implement, erk land) | Slack bot agent (multi-turn conversations) |

No code sharing between the two - they serve different use cases.

**Source**: `packages/erkbot/src/erkbot/agent/` for AgentEvent system
**Docs**: `docs/learned/integrations/erkbot/agent-event-system.md` for details
```

---

### LOW Priority

#### 8. LBYL Guidance for SDK Dataclasses

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE (add guidance)
**Source:** [PR #8070 comments]

**Draft Content:**

Add to the LBYL section in conventions.md:

```markdown
### SDK Dataclasses with Required Fields

When SDK dataclasses define required (non-Optional) fields, an `isinstance()` check is sufficient LBYL. If an object passes `isinstance(obj, SDKType)`, its required fields are guaranteed present by the SDK's construction guarantees. No need for redundant `hasattr()` or `.get()` checks on required fields.
```

---

#### 9. Review Automation Reference

**Location:** `docs/learned/reviews/review-automation-reference.md`
**Action:** CREATE
**Source:** [PR #8070 comments]

**Draft Content:**

```markdown
---
title: Review Automation Reference
read_when:
  - interpreting automated review feedback
  - understanding false positive patterns
  - deciding whether to address or override review comments
---

# Review Automation Reference

Guide to automated code review bots and their feedback patterns.

## Common False Positives

### SDK Dataclass Field Access

When accessing fields on SDK-provided dataclasses with required (non-Optional) fields, LBYL reviews may flag "missing existence check". This is a false positive - isinstance() check on the SDK type is sufficient because required fields are guaranteed by construction.

## When to Override vs Address

- **Override**: When the review misunderstands SDK type guarantees or erk conventions
- **Address**: When the review identifies genuine missing validation or error handling

Document override decisions in PR comments for future reference.
```

---

#### 10. SHOULD_BE_CODE: Event Type Field Documentation

**Location:** `packages/erkbot/src/erkbot/agent/events.py`
**Action:** CODE_CHANGE
**Source:** [Gap Analysis]

**What to add:** Docstrings on each frozen dataclass explaining field meanings. The agent-event-system.md doc should focus on conceptual patterns and design decisions. Field-level API reference belongs in the source code docstrings.

Example:

```python
@dataclass(frozen=True)
class ToolStart:
    """Tool generation has started.

    Emitted when the model begins generating a tool call (content_block_start
    with tool_use type). This is NOT tool execution - it's the model forming
    the tool call parameters.

    Attributes:
        tool_name: The name of the tool being called.
        tool_use_id: Unique identifier for this tool use block.
    """
    tool_name: str
    tool_use_id: str
```

---

## Contradiction Resolutions

No contradictions found. The existing documentation check confirmed this is a genuinely new topic area (erkbot agent integration) with no conflicting guidance in existing docs.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Workspace Package Dependency Sync

**What happened:** Running `uv sync` at the repository root after adding `claude-agent-sdk` to erkbot's pyproject.toml did not install the new dependency.

**Root cause:** Root-level `uv sync` may not detect changes in workspace package dependencies. The uv lock detection sees the root workspace as unchanged.

**Prevention:** Always use `uv sync --package <package-name>` when adding dependencies to workspace packages.

**Recommendation:** TRIPWIRE - this is non-obvious, affects all workspace packages, and causes confusing "module not found" errors.

### 2. SDK Type Assumptions

**What happened:** Initial implementation might have assumed SDK message types have typed attributes based on training data.

**Root cause:** Training data about SDKs may be outdated or different from actual current SDK implementation.

**Prevention:** Use Explore agent or WebFetch to fetch official SDK documentation before implementing. Test imports early to catch misunderstandings.

**Recommendation:** ADD_TO_DOC - document the research-first pattern in agent-event-system.md.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Claude Agent SDK StreamEvent.event dict access

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before integrating Claude Agent SDK or adding claude-agent-sdk dependency

**Warning:** `StreamEvent.event` is `dict[str, Any]` - use `.get("key")` for access, NOT attribute access. Transitive dependencies include cffi 2.0.0 (large binary wheels).

**Target doc:** `docs/learned/integrations/erkbot/tripwires.md`

This is tripwire-worthy because using attribute access (e.g., `event.type`) instead of dict access (e.g., `event.get("type")`) raises AttributeError at runtime, not caught by type checker. The SDK's type hints suggest typed access but the actual runtime type is dict.

### 2. Workspace package dependency sync

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, External tool quirk +1)

**Trigger:** Before running `uv sync` after adding dependencies to workspace packages

**Warning:** Root `uv sync` may not detect changes in workspace package dependencies. Use `uv sync --package <package-name>` to force package-specific sync.

**Target doc:** `docs/learned/architecture/tripwires.md`

This affects all workspace packages in the monorepo (erkbot, erk-shared, etc.) and causes confusing import errors when the dependency appears to be added but isn't installed.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. SDK integration research-first pattern

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)

**Notes:** Good practice pattern but not destructive if violated - just leads to potential rework. Better as documentation guidance in agent-event-system.md than a tripwire. Does not meet the threshold for cross-cutting impact or silent failure.

### 2. ToolEnd = "generated" not "executed" semantic

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)

**Notes:** Important semantic distinction but specific to this event system, not cross-cutting across erk. The naming could mislead developers into thinking ToolEnd means execution completed. Include prominently in event system docs but not as tripwire since it only affects erkbot agent code.

## Implementation Notes

### Read-When Conditions Summary

New docs should include these read-when conditions:

- **agent-event-system.md**: Working on erkbot agent integration, adding new event types, integrating Claude Agent SDK, understanding erkbot architecture
- **agent-stream-converter.md**: Debugging event stream conversion, modifying state machine, troubleshooting missing/duplicate events
- **agent-helpers.md**: Using helper utilities, writing event stream tests, extracting text or results
- **tripwires.md**: Adding SDK dependency, upgrading SDK version, debugging SDK parsing

### Source Pointers

All documentation uses source file references per docs/learned/documentation/source-pointers.md:

- Event types: `packages/erkbot/src/erkbot/agent/events.py` (grep for `@dataclass(frozen=True)`)
- Stream converter: `packages/erkbot/src/erkbot/agent/stream.py:30-82` (grep for `stream_agent_events`)
- Helpers: `packages/erkbot/src/erkbot/agent/helpers.py:6-25` (grep for function names)

### Cross-References to Maintain

**From new docs to existing:**
- agent-event-system.md references conventions.md (frozen dataclass pattern)
- agent-event-system.md references architecture/prompt-executor-patterns.md (comparison)
- agent-stream-converter.md references agent-event-system.md (conceptual overview)

**From existing docs to new:**
- architecture/prompt-executor-patterns.md should reference integrations/erkbot/agent-event-system.md

### Directory Creation

Create new directory: `docs/learned/integrations/erkbot/`

This follows the pattern of `integrations/codex/` for backend-specific integration documentation.
