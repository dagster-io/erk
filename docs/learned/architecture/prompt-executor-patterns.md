---
title: PromptExecutor Pattern Documentation
last_audited: "2026-02-16 14:10 PT"
audit_result: clean
read_when:
  - "launching Claude from CLI commands"
  - "deciding which PromptExecutor method to use"
  - "testing code that executes Claude CLI"
---

# PromptExecutor Pattern Documentation

The `PromptExecutor` abstraction provides multiple methods for launching Claude CLI. Understanding when to use each is critical.

## Method Comparison

| Method                        | Mechanism                         | Returns?                  | Use Case                           |
| ----------------------------- | --------------------------------- | ------------------------- | ---------------------------------- |
| `execute_interactive()`       | `os.execvp()`                     | Never (replaces process)  | Final action in a workflow         |
| `execute_prompt()`            | `subprocess.run()` with `--print` | `PromptResult`            | Non-interactive prompt execution   |
| `execute_command()`           | `subprocess.run()`                | `CommandResult`           | Programmatic command with metadata |
| `execute_command_streaming()` | `subprocess.Popen()`              | `Iterator[ExecutorEvent]` | Real-time progress tracking        |

## When to Use Each

### `execute_interactive()` - Process Replacement

Use when Claude should take over completely and the current command has no more work to do. Uses `os.execvp()` internally - **code after this NEVER executes**.

```python
# Good: Final action before process ends
executor.execute_interactive(
    worktree_path=Path("/repos/my-project"),
    dangerous=False,
    command="/erk:plan-implement",
    target_subpath=None,
)
# This line NEVER runs - process is replaced
```

### `execute_prompt()` - Non-Interactive

Use for programmatic Claude interactions that don't need a terminal. Returns structured `PromptResult` with success status and output text.

```python
# Good: Single-shot prompt for automation
result = executor.execute_prompt(
    "Generate a commit message for this diff",
    model="haiku",
    tools=["Read", "Bash"],
)
if result.success:
    print(result.output)
```

### `execute_command()` - Programmatic with Metadata

Use when you need to execute a slash command and capture metadata (PR URLs, issue numbers, etc.) without real-time streaming.

```python
# Good: Capture PR metadata from automated execution
result = executor.execute_command(
    "/erk:plan-implement",
    worktree_path=Path("/repos/my-project"),
    dangerous=False,
)
if result.success and result.pr_url:
    print(f"PR created: {result.pr_url}")
```

### `execute_command_streaming()` - Real-Time Progress

Use when you need real-time progress updates during command execution.

```python
# Good: Display progress as it happens
for event in executor.execute_command_streaming(
    "/erk:plan-implement",
    worktree_path=Path("/repos/my-project"),
    dangerous=False,
):
    match event:
        case ToolEvent(summary=s):
            print(f"Tool: {s}")
        case TextEvent(content=c):
            print(c)
```

## Testing with FakePromptExecutor

The fake tracks all calls for assertion via read-only properties.

### Assertion Properties

| Property            | Tracks                                                      |
| ------------------- | ----------------------------------------------------------- |
| `executed_commands` | `execute_command()` and `execute_command_streaming()` calls |
| `interactive_calls` | `execute_interactive()` calls                               |
| `prompt_calls`      | `execute_prompt()` calls                                    |

### Simulating Scenarios

```python
# Successful execution
executor = FakePromptExecutor(available=True)

# Claude not installed
executor = FakePromptExecutor(available=False)

# Command failure
executor = FakePromptExecutor(command_should_fail=True)

# PR creation
executor = FakePromptExecutor(
    simulated_pr_url="https://github.com/org/repo/pull/123",
    simulated_pr_number=123,
)

# Hook blocking (zero turns)
executor = FakePromptExecutor(simulated_zero_turns=True)
```

## Real-World Usage Example

<!-- Source: src/erk/cli/commands/objective_helpers.py, prompt_objective_update -->

The `erk land` command demonstrates `stream_command_with_feedback()` for optional post-operation actions. See `prompt_objective_update()` in `src/erk/cli/commands/objective_helpers.py` for the full implementation.

Key points from that function:

- Use `stream_command_with_feedback()` for live progress output during long-running operations
- Use `dangerous=True` when the user has already confirmed the action
- Handle both success and failure gracefully
- Provide fallback command for manual retry on failure

## File Locations

- **ABC**: `packages/erk-shared/src/erk_shared/core/prompt_executor.py`
- **Real**: `src/erk/core/prompt_executor.py` (ClaudePromptExecutor)
- **Fake**: `tests/fakes/prompt_executor.py` and `packages/erk-shared/src/erk_shared/core/fakes.py`

## Error Handling: Streaming stderr

ClaudePromptExecutor uses a background thread to accumulate stderr while streaming stdout:

```
┌─────────────────────────────────────────────────────────────┐
│ ClaudePromptExecutor.execute_command_streaming()              │
├─────────────────────────────────────────────────────────────┤
│ Main Thread                    │ Background Thread          │
│ ─────────────────────────────  │ ──────────────────────────│
│ process = Popen(...)           │                            │
│ for line in process.stdout:    │ for line in stderr:        │
│   yield parse(line)            │   stderr_output.append()   │
│ process.wait()                 │                            │
│ stderr_thread.join(timeout=5)  │                            │
└─────────────────────────────────────────────────────────────┘
```

This is necessary because:

1. Reading stdout blocks until EOF
2. Stderr could fill its buffer and cause deadlock
3. The thread accumulates stderr parts for the final error message

## Multi-Backend Design

The `PromptExecutor` ABC is designed to support multiple agent backends. The current sole implementation is `ClaudePromptExecutor`, but the interface is intentionally abstract enough to support others.

### Key Abstraction Points

- **`is_available()`** — Each backend checks for its own binary (`claude`, `codex`, etc.)
- **`execute_interactive()`** — Uses `os.execvp()` to replace the process. The binary name is determined by the executor implementation, not the caller. Callers should use `os.execvp(cmd_args[0], cmd_args)` rather than hardcoding `os.execvp("claude", ...)`.
- **`execute_command_streaming()`** — Each backend has its own JSONL format. The executor parses backend-specific events and yields the common `ExecutorEvent` union types.
- **`execute_prompt()`** — Backend-specific flags (e.g., `--system-prompt` for Claude, which has no Codex equivalent) are handled internally by each executor.

### Leaky Abstraction Warning

Several commands bypass `PromptExecutor` and call the `claude` binary directly via `os.execvp()`. These are tracked for refactoring:

- `src/erk/cli/commands/plan/replan_cmd.py`
- `src/erk/cli/commands/objective/implement_cmd.py`
- `src/erk/core/interactive_claude.py` (helper that builds `["claude", ...]` args)

For multi-backend support, these should route through `PromptExecutor` or a backend-aware arg builder.

### Related Codex Documentation

- [Codex CLI Reference](../integrations/codex/codex-cli-reference.md) — Flag mapping between Claude and Codex
- [Codex JSONL Format](../integrations/codex/codex-jsonl-format.md) — Codex streaming event format

## Related Topics

- [Subprocess Wrappers](subprocess-wrappers.md) - General subprocess patterns
