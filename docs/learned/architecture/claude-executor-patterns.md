---
title: ClaudeExecutor Pattern Documentation
read_when:
  - "launching Claude from CLI commands"
  - "deciding which ClaudeExecutor method to use"
  - "testing code that executes Claude CLI"
  - "choosing between RealClaudeExecutor and RealPromptExecutor"
---

# ClaudeExecutor Pattern Documentation

The `ClaudeExecutor` abstraction provides multiple methods for launching Claude CLI. Understanding when to use each is critical.

## Method Comparison

| Method                        | Mechanism                         | Returns?                 | Use Case                           |
| ----------------------------- | --------------------------------- | ------------------------ | ---------------------------------- |
| `execute_interactive()`       | `os.execvp()`                     | Never (replaces process) | Final action in a workflow         |
| `execute_prompt()`            | `subprocess.run()` with `--print` | `PromptResult`           | Non-interactive prompt execution   |
| `execute_command()`           | `subprocess.run()`                | `CommandResult`          | Programmatic command with metadata |
| `execute_command_streaming()` | `subprocess.Popen()`              | `Iterator[ClaudeEvent]`  | Real-time progress tracking        |

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

## Testing with FakeClaudeExecutor

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
executor = FakeClaudeExecutor(claude_available=True)

# Claude not installed
executor = FakeClaudeExecutor(claude_available=False)

# Command failure
executor = FakeClaudeExecutor(command_should_fail=True)

# PR creation
executor = FakeClaudeExecutor(
    simulated_pr_url="https://github.com/org/repo/pull/123",
    simulated_pr_number=123,
)

# Hook blocking (zero turns)
executor = FakeClaudeExecutor(simulated_zero_turns=True)
```

## Real-World Usage Example

The `erk land` command demonstrates `execute_command()` for optional post-operation actions:

```python
def _prompt_objective_update(
    ctx: ErkContext,
    repo_root: Path,
    objective_number: int,
    pr_number: int,
    force: bool,
) -> None:
    """Prompt user to update objective after landing."""
    user_output(f"   Linked to Objective #{objective_number}")

    if force:
        # --force skips prompts, show command for later
        user_output("   Run '/erk:objective-update-with-landed-pr' to update objective")
        return

    # User chooses to run now
    result = ctx.claude_executor.execute_command(
        "/erk:objective-update-with-landed-pr",
        repo_root,
        dangerous=True,  # Skip permission prompts for non-interactive
    )
    if result.success:
        user_output(click.style("✓", fg="green") + " Objective updated")
    else:
        user_output(
            click.style("⚠", fg="yellow")
            + f" Objective update failed: {result.error_message}"
        )
```

Key points:

- Use `dangerous=True` when the user has already confirmed the action
- Handle both success and failure gracefully
- Provide fallback command for manual retry on failure

## File Locations

- **ABC**: `packages/erk-shared/src/erk_shared/core/claude_executor.py`
- **Real**: `src/erk/core/claude_executor.py` (RealClaudeExecutor)
- **Fake**: `tests/fakes/claude_executor.py`

## Executor Comparison: ClaudeExecutor vs PromptExecutor

Erk has two distinct executor abstractions for Claude CLI operations:

| Aspect                 | RealClaudeExecutor                                      | RealPromptExecutor                                           |
| ---------------------- | ------------------------------------------------------- | ------------------------------------------------------------ |
| **Location**           | `src/erk/core/claude_executor.py`                       | `packages/erk-shared/src/erk_shared/prompt_executor/real.py` |
| **Scope**              | Full-featured: interactive, streaming, commands         | Single-shot prompts only                                     |
| **Methods**            | 4 methods (interactive, streaming, prompt, passthrough) | 1 method (execute_prompt)                                    |
| **Retry logic**        | No built-in retry                                       | Automatic retry on empty output                              |
| **Error accumulation** | Background thread for stderr                            | Simple capture                                               |
| **Dependencies**       | Console gateway                                         | Time gateway (for retry delays)                              |
| **Use case**           | CLI commands launching Claude                           | Programmatic single prompts                                  |

### When to Use Each

**Use RealClaudeExecutor when:**

- Launching Claude interactively (`execute_interactive`)
- Need real-time streaming events (`execute_command_streaming`)
- Executing slash commands with metadata extraction (`execute_command`)
- Running in a CLI context with terminal output

**Use RealPromptExecutor when:**

- Simple single-shot prompts for automation
- Need automatic retry on transient failures
- Lightweight operations (no streaming, no metadata)
- Testability with FakeTime is important

### Error Handling Differences

RealClaudeExecutor uses a background thread to accumulate stderr while streaming stdout:

```
┌─────────────────────────────────────────────────────────────┐
│ RealClaudeExecutor.execute_command_streaming()              │
├─────────────────────────────────────────────────────────────┤
│ Main Thread                    │ Background Thread          │
│ ─────────────────────────────  │ ──────────────────────────│
│ process = Popen(...)           │                            │
│ for line in process.stdout:    │ for line in stderr:        │
│   yield parse(line)            │   stderr_output.append()   │
│ process.wait()                 │                            │
│ stderr_thread.join(timeout=5)  │                            │
│ # Use accumulated stderr       │                            │
└─────────────────────────────────────────────────────────────┘
```

This is necessary because:

1. Reading stdout blocks until EOF
2. Stderr could fill its buffer and cause deadlock
3. The thread accumulates stderr parts for the final error message

RealPromptExecutor uses simple `capture_output=True` since there's no streaming.

## Related Topics

- [Subprocess Wrappers](subprocess-wrappers.md) - General subprocess patterns
