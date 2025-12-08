---
title: ClaudeExecutor Patterns
read_when:
  - "launching Claude CLI from Python code"
  - "implementing interactive Claude workflows"
  - "deciding between execute_interactive vs execute_interactive_command"
  - "testing commands that launch Claude"
---

# ClaudeExecutor Patterns

The `ClaudeExecutor` abstraction provides multiple methods for launching the Claude CLI. Understanding when to use each is critical for correct behavior and testability.

## Method Comparison

| Method                          | Mechanism                         | Returns?                 | Use Case                         |
| ------------------------------- | --------------------------------- | ------------------------ | -------------------------------- |
| `execute_interactive()`         | `os.execvp()`                     | Never (replaces process) | Final action in a workflow       |
| `execute_interactive_command()` | `subprocess.run()`                | Exit code                | When control must return         |
| `execute_prompt()`              | `subprocess.run()` with `--print` | `PromptResult`           | Non-interactive prompt execution |

## When to Use Each

### `execute_interactive()` - Process Replacement

Use when Claude should take over completely and the current command has no more work.

**Mechanism**: Uses `os.execvp()` internally - **code after this NEVER executes**.

**Example use case**: `erk objective turn` launches Claude as the final action.

```python
# This is the LAST line that executes
context.claude.execute_interactive(
    prompt=evaluation_prompt,
    resume_id=resume_id
)
# Code here NEVER runs - process has been replaced
```

**Critical**: Do NOT use this if you need to perform cleanup, logging, or any other action after Claude exits.

### `execute_interactive_command()` - Subprocess with Return

Use when you need control to return after Claude exits.

**Mechanism**: Uses `subprocess.run()` internally, returns exit code.

**Example use case**: Running Claude as a step in a multi-step workflow.

```python
exit_code = context.claude.execute_interactive_command(
    prompt=planning_prompt
)
# Code here DOES run - control has returned
if exit_code != 0:
    log_failure()
```

**Critical**: This is more expensive than `execute_interactive()` but necessary when you need post-processing.

### `execute_prompt()` - Non-Interactive

Use for programmatic Claude interactions that don't need a terminal.

**Mechanism**: Uses `subprocess.run()` with `--print` flag, captures output.

**Example use case**: Automated processing or background tasks.

```python
result = context.claude.execute_prompt(
    prompt="Analyze this file",
    model="haiku"
)
# result.stdout contains Claude's response
```

## Testing with FakeClaudeExecutor

The fake tracks all calls for assertion via the `interactive_command_calls` list.

```python
from tests.fakes.claude_executor import FakeClaudeExecutor

fake = FakeClaudeExecutor()
context = build_context(claude=fake)

# Run command that calls Claude
run_my_command(context)

# Assert Claude was invoked correctly
assert len(fake.interactive_command_calls) == 1
assert "my-prompt" in fake.interactive_command_calls[0]["prompt"]
```

**Note**: The fake does NOT simulate `execute_interactive()` (process replacement) - it cannot be tested this way. Commands using `execute_interactive()` should have minimal logic after the call (ideally none).

## File Locations

- **Interface**: `src/erk/core/claude_executor.py` (ClaudeExecutor ABC)
- **Real implementation**: `src/erk/core/claude_executor.py` (RealClaudeExecutor)
- **Fake**: `tests/fakes/claude_executor.py` (FakeClaudeExecutor)

## Related Documentation

- [Erk Architecture Patterns](erk-architecture.md) — dependency injection patterns
- [Fake-Driven Testing](../testing/overview.md) — testing philosophy
