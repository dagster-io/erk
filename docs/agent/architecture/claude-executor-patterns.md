---
title: ClaudeExecutor Pattern Documentation
read_when:
  - "launching Claude from CLI commands"
  - "deciding which ClaudeExecutor method to use"
  - "testing code that executes Claude CLI"
tripwires:
  - action: "choosing between execute_interactive and execute_interactive_command"
    warning: "execute_interactive() NEVER returns (uses os.execvp). Use execute_interactive_command() if you need control to return."
---

# ClaudeExecutor Pattern Documentation

The `ClaudeExecutor` abstraction provides multiple methods for launching Claude CLI. Understanding when to use each is critical.

## Method Comparison

| Method                          | Mechanism                         | Returns?                 | Use Case                           |
| ------------------------------- | --------------------------------- | ------------------------ | ---------------------------------- |
| `execute_interactive()`         | `os.execvp()`                     | Never (replaces process) | Final action in a workflow         |
| `execute_interactive_command()` | `subprocess.run()`                | Exit code                | When control must return           |
| `execute_prompt()`              | `subprocess.run()` with `--print` | `PromptResult`           | Non-interactive prompt execution   |
| `execute_command()`             | `subprocess.run()`                | `CommandResult`          | Programmatic command with metadata |
| `execute_command_streaming()`   | `subprocess.Popen()`              | `Iterator[ClaudeEvent]`  | Real-time progress tracking        |

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

### `execute_interactive_command()` - Subprocess with Return

Use when you need control to return after Claude exits. Uses `subprocess.run()` internally, returns exit code. The user can interact with Claude during execution.

```python
# Good: Continue processing after Claude finishes
exit_code = executor.execute_interactive_command(
    command="/erk:create-extraction-plan",
    worktree_path=Path("/repos/my-project"),
    dangerous=True,
)
if exit_code == 0:
    print("Plan created successfully")
    # Continue with more work...
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

| Property                    | Tracks                                                      |
| --------------------------- | ----------------------------------------------------------- |
| `executed_commands`         | `execute_command()` and `execute_command_streaming()` calls |
| `interactive_calls`         | `execute_interactive()` calls                               |
| `interactive_command_calls` | `execute_interactive_command()` calls                       |
| `prompt_calls`              | `execute_prompt()` calls                                    |

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

# Interactive command with specific exit code
executor = FakeClaudeExecutor(interactive_command_exit_code=1)

# Hook blocking (zero turns)
executor = FakeClaudeExecutor(simulated_zero_turns=True)
```

## File Locations

- **Interface**: `src/erk/core/claude_executor.py` (ClaudeExecutor ABC)
- **Fake**: `tests/fakes/claude_executor.py`

## Related Topics

- [Subprocess Wrappers](subprocess-wrappers.md) - General subprocess patterns
