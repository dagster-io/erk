---
title: ClaudeExecutor Pattern Documentation
read_when:
  - "launching Claude from CLI commands"
  - "deciding which ClaudeExecutor method to use"
  - "testing code that executes Claude CLI"
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
    command="/erk:system:impl-execute",
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
    "/erk:system:impl-execute",
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
    "/erk:system:impl-execute",
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

## Related Topics

- [Subprocess Wrappers](subprocess-wrappers.md) - General subprocess patterns
