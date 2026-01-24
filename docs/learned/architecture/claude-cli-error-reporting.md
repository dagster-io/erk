---
title: Claude CLI Error Reporting
read_when:
  - "handling Claude CLI errors"
  - "interpreting PromptResult.error"
  - "working with ErrorEvent, NoOutputEvent, NoTurnsEvent, ProcessErrorEvent"
tripwires:
  - action: "modifying Claude CLI error reporting or PromptResult.error format"
    warning: "Error messages must maintain structured format with exit code, stderr, and context. Changes affect all callers of execute_prompt() and execute_command_streaming()."
---

# Claude CLI Error Reporting

Error handling for Claude CLI execution uses typed events and structured error messages to enable precise diagnosis of failures.

## Error Event Types

Claude CLI execution produces four distinct error event types, defined in `erk_shared.core.claude_executor`:

| Event Type          | Field             | Meaning                                           |
| ------------------- | ----------------- | ------------------------------------------------- |
| `ErrorEvent`        | `message: str`    | Non-zero exit code during execution               |
| `NoOutputEvent`     | `diagnostic: str` | Command completed but produced no output          |
| `NoTurnsEvent`      | `diagnostic: str` | Command completed with num_turns=0 (hook blocked) |
| `ProcessErrorEvent` | `message: str`    | Failed to start process or timeout                |

## Error Message Structure

Error messages follow a structured format with contextual information:

**ErrorEvent format:**

```
Claude command {command} failed
  Exit code: {returncode}
  Lines processed: {line_count}
  Stderr:
{stderr_content}
```

**NoOutputEvent format:**

```
Claude command {command} completed but produced no output
  Exit code: {returncode}
  Working directory: {worktree_path}
  Stderr:
{stderr_content}
```

**NoTurnsEvent format:**

```
Claude command {command} completed without processing
  This usually means a hook blocked the command
  Run 'claude' directly to see hook error messages
  Working directory: {worktree_path}
```

**ProcessErrorEvent format:**

```
Failed to start Claude CLI: {os_error}
Command: {full_command}
```

## PromptResult Error Handling

For single-shot prompts via `execute_prompt()`, errors are returned in `PromptResult.error`:

```python
result = executor.execute_prompt(prompt, model="haiku", ...)
if not result.success:
    # result.error contains stderr or "Exit code N" fallback
    print(f"Failed: {result.error}")
```

The error field contains:

1. `stderr.strip()` if stderr has content
2. `"Exit code {N}"` as fallback if stderr is empty

## Handling Errors

Pattern match on event types for comprehensive error handling:

```python
for event in executor.execute_command_streaming(...):
    match event:
        case ErrorEvent(message=msg):
            # Non-zero exit - command ran but failed
            handle_error(msg)
        case NoOutputEvent(diagnostic=diag):
            # Silent failure - no output produced
            handle_no_output(diag)
        case NoTurnsEvent(diagnostic=diag):
            # Hook blocking - command was prevented
            handle_blocked(diag)
        case ProcessErrorEvent(message=msg):
            # Startup failure - couldn't run command
            handle_process_error(msg)
```

## Common Failure Modes

| Symptom                 | Likely Cause                | Event Type          |
| ----------------------- | --------------------------- | ------------------- |
| Exit code 1 with stderr | Claude CLI validation error | `ErrorEvent`        |
| Zero output, exit 0     | LLM returned empty response | `NoOutputEvent`     |
| num_turns=0             | Hook rejected the command   | `NoTurnsEvent`      |
| OSError on Popen        | Claude CLI not installed    | `ProcessErrorEvent` |
| Timeout after 10 min    | Long-running command hung   | `ProcessErrorEvent` |

## Implementation Locations

- **Event types**: `packages/erk-shared/src/erk_shared/core/claude_executor.py`
- **Streaming execution**: `src/erk/core/claude_executor.py` (`execute_command_streaming`)
- **Single prompt**: `src/erk/core/claude_executor.py` (`execute_prompt`)
- **Lightweight prompts**: `packages/erk-shared/src/erk_shared/prompt_executor/real.py`

## Related Topics

- [glossary.md](../glossary.md) - Full event type reference table
- [claude-executor-patterns.md](claude-executor-patterns.md) - ClaudeExecutor usage patterns
- [claude-cli-integration.md](claude-cli-integration.md) - CLI flag requirements
