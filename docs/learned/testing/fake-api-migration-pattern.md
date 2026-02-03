---
title: Fake API Migration Pattern - PromptExecutor Consolidation
last_audited: "2026-02-03 03:56 PT"
audit_result: edited
tripwires:
  - action: "using old FakePromptExecutor API patterns in new tests"
    warning: "Use simulated_* parameters (new API), not output=/should_fail= (old gateway API). See migration table."
read_when:
  - "Writing tests for prompt executor functionality"
  - "Migrating old PromptExecutor tests after consolidation"
  - "Understanding FakePromptExecutor constructor API"
---

# Fake API Migration Pattern: PromptExecutor Consolidation

## Overview

After the PromptExecutor consolidation (PR #6587), the `FakePromptExecutor` API changed from a simple `output=` / `should_fail=` pattern (gateway) to a richer API with granular control over execution scenarios (core).

## Old Pattern (Deleted Gateway FakePromptExecutor)

The deleted gateway `FakePromptExecutor` had a minimal API:

```python
# OLD PATTERN (no longer exists)
from erk_shared.gateway.prompt_executor.fake import FakePromptExecutor

# Successful execution with output
executor = FakePromptExecutor(output='["step 1", "step 2"]')

# Failure
executor = FakePromptExecutor(should_fail=True, error="API rate limit")

# Transient failures (empty output retry pattern)
executor = FakePromptExecutor(output="Success", transient_failures=2)
```

**Key characteristics:**

- Simple constructor with 3-4 parameters
- `output` field returns fixed string
- `should_fail` boolean for errors
- `transient_failures` for retry simulation

## New Pattern (Consolidated FakePromptExecutor)

The new `FakePromptExecutor` (in `tests/fakes/prompt_executor.py`) provides fine-grained control over all execution modes:

```python
# NEW PATTERN (current)
from tests.fakes.prompt_executor import FakePromptExecutor

# Successful execution with custom output
executor = FakePromptExecutor(
    available=True,
    simulated_prompt_output='["step 1", "step 2"]'
)

# Command failure
executor = FakePromptExecutor(
    available=True,
    command_should_fail=True
)

# PR creation simulation
executor = FakePromptExecutor(
    available=True,
    simulated_pr_url="https://github.com/org/repo/pull/123",
    simulated_pr_number=123,
    simulated_pr_title="Add feature"
)

# Hook blocking (zero turns)
executor = FakePromptExecutor(
    available=True,
    simulated_zero_turns=True
)

# Tool events
executor = FakePromptExecutor(
    available=True,
    simulated_tool_events=["Using Read tool", "Using Bash tool"]
)
```

**Key characteristics:**

- Rich constructor with 10+ simulation parameters
- `simulated_*` prefix for clarity
- Separate flags for different failure modes
- Supports all 4 execution modes (interactive, streaming, command, prompt)

## Migration Mapping

| Old Gateway API        | New Core API                                                     |
| ---------------------- | ---------------------------------------------------------------- |
| `output="text"`        | `simulated_prompt_output="text"`                                 |
| `should_fail=True`     | `command_should_fail=True` (for commands)                        |
| `error="message"`      | `simulated_prompt_error="message"` (for prompts)                 |
| `transient_failures=2` | Not directly supported (retry logic moved to RealPromptExecutor) |
| N/A                    | `simulated_pr_url=...` (new PR metadata support)                 |
| N/A                    | `simulated_zero_turns=True` (new hook blocking support)          |
| N/A                    | `simulated_tool_events=[...]` (new streaming event support)      |

## Migration Examples

### Example 1: Simple Prompt Execution

**Before (gateway):**

```python
executor = FakePromptExecutor(output='["extracted", "steps"]')
result = executor.execute_prompt("Extract steps from code", model="haiku")
assert result.success
assert result.output == '["extracted", "steps"]'
```

**After (core):**

```python
executor = FakePromptExecutor(simulated_prompt_output='["extracted", "steps"]')
result = executor.execute_prompt("Extract steps from code", model="haiku", cwd=Path("/repo"))
assert result.success
assert result.output == '["extracted", "steps"]'
```

### Example 2: Failure Simulation

**Before (gateway):**

```python
executor = FakePromptExecutor(should_fail=True, error="API timeout")
result = executor.execute_prompt("test", model="haiku")
assert not result.success
assert result.error == "API timeout"
```

**After (core):**

```python
# For prompt failures
executor = FakePromptExecutor(simulated_prompt_error="API timeout")
result = executor.execute_prompt("test", model="haiku", cwd=Path("/repo"))
assert not result.success
assert result.error == "API timeout"

# For command failures
executor = FakePromptExecutor(command_should_fail=True)
try:
    executor.execute_command("/test", Path("/repo"), dangerous=False)
    assert False, "Should have raised"
except RuntimeError as e:
    assert "Simulated command failure" in str(e)
```

### Example 3: Sequential Calls (Multiple Outputs)

**Before (gateway):**

```python
executor = FakePromptExecutor(outputs=["First response", "Second response"])
result1 = executor.execute_prompt("first call", model="haiku")
assert result1.output == "First response"
result2 = executor.execute_prompt("second call", model="haiku")
assert result2.output == "Second response"
```

**After (core):**

The new API doesn't support sequential outputs directly. If your test needs this, consider:

1. **Use multiple executors** - Create separate fakes for each call
2. **Use command streaming** - Emit different TextEvents in sequence
3. **Redesign the test** - Question whether sequential LLM calls should be tested separately

```python
# Option 1: Separate executors
executor1 = FakePromptExecutor(simulated_prompt_output="First response")
executor2 = FakePromptExecutor(simulated_prompt_output="Second response")
result1 = executor1.execute_prompt("first call", model="haiku", cwd=Path("/repo"))
result2 = executor2.execute_prompt("second call", model="haiku", cwd=Path("/repo"))
```

## New Capabilities

The consolidated fake adds capabilities not present in the gateway version:

### PR Metadata Simulation

```python
executor = FakePromptExecutor(
    simulated_pr_url="https://github.com/org/repo/pull/456",
    simulated_pr_number=456,
    simulated_pr_title="Implement feature X",
    simulated_issue_number=123
)
result = executor.execute_command("/erk:plan-implement", Path("/repo"), dangerous=False)
assert result.pr_url == "https://github.com/org/repo/pull/456"
assert result.pr_number == 456
```

### Hook Blocking Simulation

```python
# Simulate hook blocking the execution (num_turns=0)
executor = FakePromptExecutor(simulated_zero_turns=True)
result = executor.execute_command("/test", Path("/repo"), dangerous=False)
assert not result.success
assert result.error_message  # Contains "completed with num_turns=0"
```

### Streaming Events Simulation

```python
executor = FakePromptExecutor(
    simulated_tool_events=["Using Read tool", "Using Bash tool"],
    simulated_pr_url="https://github.com/org/repo/pull/789"
)
events = list(executor.execute_command_streaming("/test", Path("/repo"), dangerous=False))
# Events include ToolEvent, TextEvent, PrUrlEvent, etc.
```

## Test Assertion Patterns

The new fake tracks all calls for verification:

```python
executor = FakePromptExecutor()

# Execute various operations
executor.execute_interactive(Path("/repo"), dangerous=False, command="/test")
executor.execute_command("/test", Path("/repo"), dangerous=False)
executor.execute_prompt("test prompt", model="haiku", cwd=Path("/repo"))

# Assert on tracked calls
assert len(executor.interactive_calls) == 1
assert len(executor.executed_commands) == 1
assert len(executor.prompt_calls) == 1

# Inspect call details
interactive_call = executor.interactive_calls[0]
assert interactive_call.command == "/test"
assert not interactive_call.dangerous
```

## Why the API Changed

The consolidation merged two different abstractions:

1. **Gateway PromptExecutor** (simple, single-shot prompts)
2. **ClaudeExecutor** (full-featured, interactive, streaming)

The new API reflects the richer capabilities of the full-featured executor:

- **Multiple execution modes** (interactive, streaming, command, prompt)
- **Metadata extraction** (PR numbers, issue numbers, titles)
- **Event streaming** (tool events, spinner updates, text chunks)
- **Hook interaction** (zero turns detection)
- **Process error simulation** (exit codes, stderr output)

## Related Documentation

- [PromptExecutor Patterns](../architecture/prompt-executor-patterns.md) - Complete usage guide
- [Fake-Driven Testing](fake-driven-testing.md) - Testing philosophy and fake patterns
- [Linked Mutation Tracking](linked-mutation-tracking.md) - How fakes coordinate state
