---
title: PromptExecutor Pattern Documentation
read_when:
  - "launching Claude from CLI commands"
  - "deciding which PromptExecutor method to use"
  - "testing code that executes Claude CLI"
  - "choosing between ClaudePromptExecutor and RealPromptExecutor"
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

The `erk land` command demonstrates `stream_command_with_feedback()` for optional post-operation actions. This wrapper around `execute_command_streaming()` provides live progress output:

```python
def prompt_objective_update(
    ctx: ErkContext,
    *,
    repo_root: Path,
    objective_number: int,
    pr_number: int,
    branch: str,
    force: bool,
) -> None:
    """Prompt user to update objective after landing."""
    user_output(f"   Linked to Objective #{objective_number}")

    cmd = (
        f"/erk:objective-update-with-landed-pr "
        f"--pr {pr_number} --objective {objective_number} --branch {branch} --auto-close"
    )

    if force:
        # --force skips prompt but still executes the update
        user_output("Starting objective update...")
        result = stream_command_with_feedback(
            executor=ctx.prompt_executor,
            command=cmd,
            worktree_path=repo_root,
            dangerous=True,
        )
    else:
        if not ctx.console.confirm("Update objective now?", default=True):
            user_output(f"Skipped. To update later, run:\n  {cmd}")
            return
        result = stream_command_with_feedback(
            executor=ctx.prompt_executor,
            command=cmd,
            worktree_path=repo_root,
            dangerous=True,
        )

    if result.success:
        user_output(click.style("✓", fg="green") + " Objective updated successfully")
    else:
        user_output(
            click.style("⚠", fg="yellow")
            + f" Objective update failed: {result.error_message}"
        )
```

Key points:

- Use `stream_command_with_feedback()` for live progress output during long-running operations
- Use `dangerous=True` when the user has already confirmed the action
- Handle both success and failure gracefully
- Provide fallback command for manual retry on failure

## File Locations

- **ABC**: `packages/erk-shared/src/erk_shared/core/prompt_executor.py`
- **Real**: `src/erk/core/prompt_executor.py` (ClaudePromptExecutor)
- **Fake**: `tests/fakes/prompt_executor.py`

## Executor Comparison: Core vs Gateway PromptExecutor

**IMPORTANT:** Erk has two distinct `PromptExecutor` implementations in different packages. Always use fully-qualified names to avoid confusion:

- **`erk_shared.core.prompt_executor.PromptExecutor`** - Core ABC (this doc's focus)
- **`erk_shared.gateway.prompt_executor.abc.PromptExecutor`** - Gateway ABC (different abstraction)

### Core PromptExecutor (erk_shared.core)

**Purpose:** Launch Claude CLI directly for CLI commands and interactive sessions.

**Implementations:**

- **ABC**: `erk_shared.core.prompt_executor.PromptExecutor`
- **Real**: `erk.core.prompt_executor.ClaudePromptExecutor`
- **Fake**: `tests.fakes.prompt_executor.FakePromptExecutor`

**Methods:** 4 execution modes (interactive, streaming, command, prompt)

**Use cases:** CLI commands, interactive sessions, real-time progress

### Gateway PromptExecutor (erk_shared.gateway)

**Purpose:** Provide single-shot prompt execution through the gateway layer.

**Implementations:**

- **ABC**: `erk_shared.gateway.prompt_executor.abc.PromptExecutor`
- **Real**: `erk_shared.gateway.prompt_executor.real.RealPromptExecutor`
- **Fake**: `erk_shared.gateway.prompt_executor.fake.FakePromptExecutor`

**Methods:** 1 execution mode (execute_prompt only)

**Use cases:** Programmatic prompts, retry logic, lightweight operations

### Comparison Table

| Aspect                 | Core (ClaudePromptExecutor)                         | Gateway (RealPromptExecutor)                                         |
| ---------------------- | --------------------------------------------------- | -------------------------------------------------------------------- |
| **Location**           | `src/erk/core/prompt_executor.py`                   | `packages/erk-shared/src/erk_shared/gateway/prompt_executor/real.py` |
| **Scope**              | Full-featured: interactive, streaming, commands     | Single-shot prompts only                                             |
| **Methods**            | 4 methods (interactive, streaming, command, prompt) | 1 method (execute_prompt)                                            |
| **Retry logic**        | No built-in retry                                   | Automatic retry on empty output                                      |
| **Error accumulation** | Background thread for stderr                        | Simple capture                                                       |
| **Dependencies**       | Console gateway                                     | Time gateway (for retry delays)                                      |
| **Use case**           | CLI commands launching Claude                       | Programmatic single prompts                                          |

### When to Use Each

**Use Core PromptExecutor (ClaudePromptExecutor) when:**

- Launching Claude interactively (`execute_interactive`)
- Need real-time streaming events (`execute_command_streaming`)
- Executing slash commands with metadata extraction (`execute_command`)
- Running in a CLI context with terminal output

**Use Gateway PromptExecutor (RealPromptExecutor) when:**

- Simple single-shot prompts for automation
- Need automatic retry on transient failures
- Lightweight operations (no streaming, no metadata)
- Testability with FakeTime is important

### Error Handling Differences

Core PromptExecutor (ClaudePromptExecutor) uses a background thread to accumulate stderr while streaming stdout:

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

Gateway PromptExecutor (RealPromptExecutor) uses simple `capture_output=True` since there's no streaming.

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
- `src/erk/cli/commands/objective/next_plan_cmd.py`
- `src/erk/cli/commands/objective/reconcile_cmd.py`
- `src/erk/core/interactive_claude.py` (helper that builds `["claude", ...]` args)

For multi-backend support, these should route through `PromptExecutor` or a backend-aware arg builder.

### Related Codex Documentation

- [Codex CLI Reference](../integrations/codex/codex-cli-reference.md) — Flag mapping between Claude and Codex
- [Codex JSONL Format](../integrations/codex/codex-jsonl-format.md) — Codex streaming event format

## Related Topics

- [Subprocess Wrappers](subprocess-wrappers.md) - General subprocess patterns
