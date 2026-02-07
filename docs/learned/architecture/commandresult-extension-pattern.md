---
title: CommandResult Extension Pattern
read_when:
  - "adding new field to CommandResult"
  - "extending CommandResult dataclass"
  - "adding metadata extraction"
  - "implementing new CommandResult field"
---

# CommandResult Extension Pattern

## Overview

This document provides a step-by-step checklist for adding new metadata fields to the `CommandResult` dataclass. The pattern ensures metadata flows correctly through the entire parsing and execution pipeline.

## When to Use This Pattern

Use this pattern when you need to:

- Extract new metadata from Claude CLI's stream-json output
- Add tracking for new PR/issue attributes
- Capture execution metadata not currently in CommandResult
- Enable new functionality that depends on command execution data

## Complete Checklist

Follow these 8 steps in order to add a new CommandResult field:

### 1. Add Field to CommandResult Dataclass

**File:** `src/erk/core/claude_executor.py`

Add the new field to the `CommandResult` dataclass with a default value of `None`:

```python
@dataclass
class CommandResult:
    """Result of executing a Claude CLI command.

    Attributes:
        success: Whether the command completed successfully
        pr_url: Pull request URL if one was created, None otherwise
        pr_number: Pull request number if one was created, None otherwise
        pr_title: Pull request title if one was created, None otherwise
        issue_number: GitHub issue number if one was linked, None otherwise
        session_id: Claude session ID from stream-json output
        duration_seconds: Execution time in seconds
        error_message: Error description if command failed, None otherwise
        filtered_messages: List of text messages and tool summaries for display
    """

    success: bool
    pr_url: str | None
    pr_number: int | None
    pr_title: str | None
    issue_number: int | None
    session_id: str | None  # <-- NEW FIELD
    duration_seconds: float
    error_message: str | None
    filtered_messages: list[str] = field(default_factory=list)
```

### 2. Add Field to `_parse_stream_json_line()` Result Dict

**File:** `src/erk/core/claude_executor.py`

Initialize the field in the result dictionary returned by `_parse_stream_json_line()`:

```python
def _parse_stream_json_line(
    self, line: str, worktree_path: Path, command: str
) -> dict[str, str | int | None] | None:
    """Parse a single stream-json line and extract relevant information."""
    # ... JSON parsing logic ...

    result: dict[str, str | int | None] = {
        "text_content": None,
        "tool_summary": None,
        "spinner_update": None,
        "pr_url": None,
        "pr_number": None,
        "pr_title": None,
        "issue_number": None,
        "session_id": None,  # <-- NEW FIELD
    }

    # ... extraction logic ...
```

### 3. Add Extraction Logic in `_parse_stream_json_line()`

**File:** `src/erk/core/claude_executor.py`

Add logic to extract the field from the JSON data:

```python
def _parse_stream_json_line(
    self, line: str, worktree_path: Path, command: str
) -> dict[str, str | int | None] | None:
    """Parse a single stream-json line and extract relevant information."""
    # ... existing parsing ...

    # Extract session_id (appears at top level, not in message)
    session_id_value = data.get("session_id")
    if session_id_value is not None:
        result["session_id"] = str(session_id_value)

    return result
```

**CRITICAL:** Understand where data appears in stream-json structure:

- **Top-level fields** (like `session_id`): `data.get("session_id")`
- **Message content** (like text): `data.get("message", {}).get("content", [])`
- **Tool results** (like PR metadata): Check `type: "user"` messages

See [claude-cli-stream-json.md](../reference/claude-cli-stream-json.md) for complete stream-json structure.

### 4. Add `yield StreamEvent()` in `execute_command_streaming()`

**File:** `src/erk/core/claude_executor.py`

Yield a StreamEvent when the field is found:

```python
def execute_command_streaming(
    self,
    command: str,
    worktree_path: Path,
    dangerous: bool,
    verbose: bool = False,
    debug: bool = False,
) -> Iterator[StreamEvent]:
    """Execute Claude CLI command and yield StreamEvents in real-time."""
    # ... process stdout line by line ...

    for line in process.stdout:
        parsed = self._parse_stream_json_line(line, worktree_path, command)
        if parsed is None:
            continue

        # ... existing event yields ...

        # Yield session ID
        session_id_value = parsed.get("session_id")
        if session_id_value is not None:
            yield StreamEvent("session_id", str(session_id_value))
```

### 5. Add Capture Logic in `execute_command()` Method

**File:** `src/erk/core/claude_executor.py`

Capture the field from streaming events in the non-streaming wrapper:

```python
def execute_command(
    self,
    command: str,
    worktree_path: Path,
    dangerous: bool,
    verbose: bool = False,
) -> CommandResult:
    """Execute Claude CLI command and return final result (non-streaming)."""
    start_time = time.time()
    filtered_messages: list[str] = []
    pr_url: str | None = None
    pr_number: int | None = None
    pr_title: str | None = None
    issue_number: int | None = None
    session_id: str | None = None  # <-- NEW VARIABLE
    error_message: str | None = None
    success = True

    for event in self.execute_command_streaming(command, worktree_path, dangerous, verbose):
        if event.event_type == "text":
            filtered_messages.append(event.content)
        # ... existing event handlers ...
        elif event.event_type == "session_id":
            session_id = event.content  # <-- NEW HANDLER

    duration = time.time() - start_time
    return CommandResult(
        success=success,
        pr_url=pr_url,
        pr_number=pr_number,
        pr_title=pr_title,
        issue_number=issue_number,
        session_id=session_id,  # <-- NEW FIELD
        duration_seconds=duration,
        error_message=error_message,
        filtered_messages=filtered_messages,
    )
```

### 6. Update Streaming Consumer Code

If you have code that consumes streaming events and builds CommandResult, add capture logic:

```python
def execute_and_capture(
    ctx: ErkContext,
    command: str,
    worktree_path: Path,
) -> CommandResult:
    """Execute command and capture streaming events into CommandResult."""
    # ... existing setup ...
    session_id: str | None = None  # <-- NEW VARIABLE

    for event in ctx.claude_executor.execute_command_streaming(
        command=command,
        worktree_path=worktree_path,
        dangerous=ctx.dry_run,
    ):
        # ... existing event handlers ...
        if event.event_type == "session_id":
            session_id = event.content  # <-- NEW HANDLER

    # ... build CommandResult ...
    return CommandResult(
        success=success,
        pr_url=pr_url,
        pr_number=pr_number,
        pr_title=pr_title,
        issue_number=issue_number,
        session_id=session_id,  # <-- NEW FIELD
        duration_seconds=duration,
        error_message=error_message,
        filtered_messages=filtered_messages,
    )
```

### 7. Add `simulated_*` Parameter to `FakeClaudeExecutor`

**File:** `tests/fakes/fake_claude_executor.py`

Add a simulated parameter to enable testing:

```python
class FakeClaudeExecutor(ClaudeExecutor):
    """Test double for Claude CLI execution."""

    def __init__(
        self,
        simulated_available: bool = True,
        simulated_success: bool = True,
        simulated_pr_url: str | None = None,
        simulated_pr_number: int | None = None,
        simulated_pr_title: str | None = None,
        simulated_issue_number: int | None = None,
        simulated_session_id: str | None = None,  # <-- NEW PARAMETER
        simulated_error: str | None = None,
        simulated_messages: list[str] | None = None,
    ) -> None:
        self._available = simulated_available
        self._success = simulated_success
        self._pr_url = simulated_pr_url
        self._pr_number = simulated_pr_number
        self._pr_title = simulated_pr_title
        self._issue_number = simulated_issue_number
        self._session_id = simulated_session_id  # <-- NEW FIELD
        self._error = simulated_error
        self._messages = simulated_messages or []
```

Update `execute_command_streaming()` to yield the simulated value:

```python
def execute_command_streaming(
    self,
    command: str,
    worktree_path: Path,
    dangerous: bool,
    verbose: bool = False,
    debug: bool = False,
) -> Iterator[StreamEvent]:
    """Simulate streaming command execution."""
    # ... existing yields ...

    if self._session_id is not None:
        yield StreamEvent("session_id", self._session_id)

    if not self._success and self._error:
        yield StreamEvent("error", self._error)
```

### 8. Add Tests for Parsing, Fake, and Integration

Add tests to verify the field works correctly:

#### A. Parsing Test

**File:** `tests/core/test_claude_executor.py`

Test that `_parse_stream_json_line()` extracts the field correctly:

```python
def test_parse_stream_json_line_extracts_session_id():
    """Test that _parse_stream_json_line extracts session_id from top level."""
    executor = RealClaudeExecutor()
    line = json.dumps({
        "type": "assistant",
        "session_id": "abc123-def456",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello"}]
        }
    })

    result = executor._parse_stream_json_line(line, Path("/fake"), "/test")

    assert result is not None
    assert result["session_id"] == "abc123-def456"
```

#### B. Fake Test

**File:** `tests/fakes/test_fake_claude_executor.py`

Test that `FakeClaudeExecutor` simulates the field correctly:

```python
def test_fake_claude_executor_simulates_session_id():
    """Test FakeClaudeExecutor yields session_id event."""
    fake = FakeClaudeExecutor(simulated_session_id="test-session-123")

    events = list(fake.execute_command_streaming(
        command="/test",
        worktree_path=Path("/fake"),
        dangerous=False,
    ))

    session_events = [e for e in events if e.event_type == "session_id"]
    assert len(session_events) == 1
    assert session_events[0].content == "test-session-123"
```

#### C. Integration Test

**File:** `tests/core/test_claude_executor.py`

Test that `execute_command()` captures the field into `CommandResult`:

```python
def test_execute_command_captures_session_id():
    """Test execute_command captures session_id into CommandResult."""
    fake = FakeClaudeExecutor(simulated_session_id="captured-session-789")

    result = fake.execute_command(
        command="/test",
        worktree_path=Path("/fake"),
        dangerous=False,
    )

    assert result.session_id == "captured-session-789"
```

## Real-World Example: Adding `session_id`

This pattern was used to add `session_id` support to CommandResult. The changes touched these locations (see the files for current implementation):

| Step | Location                                                        | Change                                              |
| ---- | --------------------------------------------------------------- | --------------------------------------------------- |
| 1    | `src/erk/core/claude_executor.py` - CommandResult               | Add `session_id: str \| None` field                 |
| 2    | `src/erk/core/claude_executor.py` - `_parse_stream_json_line`   | Add `"session_id": None` to result dict             |
| 3    | `src/erk/core/claude_executor.py` - `_parse_stream_json_line`   | Add extraction logic for top-level `session_id`     |
| 4    | `src/erk/core/claude_executor.py` - `execute_command_streaming` | Yield `StreamEvent("session_id", ...)`              |
| 5    | `src/erk/core/claude_executor.py` - `execute_command`           | Capture event into `session_id` variable            |
| 6    | `src/erk/core/output.py` - `stream_command_with_feedback`       | Same capture logic                                  |
| 7    | `tests/fakes/fake_claude_executor.py`                           | Add `simulated_session_id` parameter                |
| 8    | Test files                                                      | Add parsing, fake simulation, and integration tests |

See `src/erk/core/claude_executor.py` for the canonical implementation.

## Common Pitfalls

### 1. Forgetting to initialize in result dict

```python
# ❌ WRONG - field not in result dict
result: dict[str, str | int | None] = {
    "text_content": None,
    "tool_summary": None,
    # Missing: "session_id": None,
}

# Later extraction will KeyError or silently fail
result["session_id"] = data.get("session_id")  # KeyError
```

### 2. Not yielding StreamEvent in execute_command_streaming

```python
# ❌ WRONG - parse but don't yield
parsed = self._parse_stream_json_line(line, worktree_path, command)
# Missing: yield StreamEvent("session_id", parsed["session_id"])

# Result: execute_command() never sees the event
```

### 3. Extracting from wrong location in JSON

```python
# ❌ WRONG - session_id is NOT in message
session_id = data.get("message", {}).get("session_id")  # None

# ✅ CORRECT - session_id is at top level
session_id = data.get("session_id")  # "abc123-def456"
```

### 4. Not updating FakeClaudeExecutor

```python
# ❌ WRONG - no way to simulate in tests
fake = FakeClaudeExecutor()  # No simulated_session_id parameter
# Tests can't verify session_id behavior
```

### 5. Skipping tests

Without tests, you won't catch:

- Parsing bugs (wrong JSON path)
- Missing event yields
- Capture logic errors
- Type conversion issues

## Related

- **Stream-JSON Format**: [claude-cli-stream-json.md](../reference/claude-cli-stream-json.md) - Complete reference for Claude CLI's stream-json output format
- **Implementation Reference**: `src/erk/core/claude_executor.py` - RealClaudeExecutor class
- **Testing Reference**: `tests/fakes/fake_claude_executor.py` - FakeClaudeExecutor test double
