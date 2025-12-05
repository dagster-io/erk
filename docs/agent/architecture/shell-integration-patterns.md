---
title: Shell Integration Patterns
read_when:
  - "implementing commands with shell integration"
  - "fixing shell integration handler issues"
  - "understanding script-first output ordering"
  - "debugging partial success in destructive commands"
---

# Shell Integration Patterns

This document covers implementation patterns for shell integration commands, complementing the [fundamental constraint](shell-integration-constraint.md) documentation.

## Handler Execution Model

The shell integration handler in `handler.py` can execute commands in two ways:

### CliRunner (In-Process)

- **Pros**: Fast, shares context with tests, no subprocess overhead
- **Cons**: Buffers ALL output (stdout AND stderr) until command completes
- **Use when**: Testing, or when real-time output isn't needed

### Subprocess (Out-of-Process)

- **Pros**: Allows real-time stderr streaming to terminal
- **Cons**: Spawns new process, can't share test context
- **Use when**: User-facing commands need live feedback

### Why Subprocess for Shell Integration

The handler uses subprocess because shell-integrated commands (like `pr land`) output progress messages that users need to see in real-time:

```python
# subprocess.run with stderr=None lets stderr stream live
result = subprocess.run(
    cmd,
    stdout=subprocess.PIPE,  # Capture for script path
    stderr=None,              # Pass through to terminal
    text=True,
    check=False,
)
```

With CliRunner, messages like "Getting current branch...", "Deleting worktree..." would all appear at once after the command completes, making it seem frozen.

## Command Routing with Subprocess

When the handler uses subprocess, commands must be invoked by their actual CLI paths, not legacy aliases.

### The Problem

Legacy aliases like `create`, `goto`, `consolidate` are registered in `SHELL_INTEGRATION_COMMANDS` for backward compatibility, but they don't exist as top-level CLI commands. The actual commands are:

| Legacy Alias  | Actual CLI Path     |
| ------------- | ------------------- |
| `create`      | `wt create`         |
| `goto`        | `wt goto`           |
| `consolidate` | `stack consolidate` |

### Solution: Map Aliases to CLI Paths

Use a dict that maps handler command names to CLI command parts:

```python
SHELL_INTEGRATION_COMMANDS: Final[dict[str, list[str]]] = {
    # Top-level commands (key matches CLI path)
    "checkout": ["checkout"],
    "up": ["up"],

    # Legacy aliases (map to actual CLI paths)
    "create": ["wt", "create"],
    "goto": ["wt", "goto"],
    "consolidate": ["stack", "consolidate"],

    # Compound commands
    "wt create": ["wt", "create"],
    "pr land": ["pr", "land"],
}
```

Then build the subprocess command from the mapped path:

```python
cli_cmd_parts = SHELL_INTEGRATION_COMMANDS.get(command_name)
cmd = ["erk", *cli_cmd_parts, *args, "--script"]
```

### Why This Matters

With the old CliRunner approach, the handler directly invoked Command objects from the dict, bypassing CLI routing. With subprocess, we go through the actual CLI, so we need proper command paths.

## Script-First Output Pattern

Commands that perform destructive operations (worktree deletion, branch deletion) MUST output their activation script **before** those operations.

### Why Script-First Matters

The handler (`handler.py`) checks for a valid script path in stdout before falling back to passthrough on failure. This enables **partial success recovery**:

```python
# From process_command_result() in handler.py
if script_path and script_exists:
    # Use script even if command had errors
    # This handles destructive commands that output script before failure
    return ShellIntegrationResult(passthrough=False, script=script_path, exit_code=exit_code)
```

If the script is output after destructive operations and an error occurs, the handler won't find a script and will passthrough—but the destructive operation already happened, leaving the shell stranded.

### BAD: Script After Destruction

```python
def dangerous_command(ctx: ErkContext, script: bool) -> None:
    # ❌ WRONG: Destructive operation first
    delete_worktree(ctx, current_worktree)
    pull_branch(ctx)  # This might fail!

    # Script output last - if pull fails, handler won't find script
    script_path = write_activation_script(dest_path)
    machine_output(script_path)  # Never reached on error
```

### GOOD: Script Before Destruction

```python
def safe_command(ctx: ErkContext, script: bool) -> None:
    # ✅ CORRECT: Output script BEFORE destructive operations
    script_content = render_activation_script(worktree_path=dest_path)
    result = ctx.script_writer.write_activation_script(script_content)
    machine_output(str(result.path), nl=False)

    # Now destructive operations - if these fail, script already exists
    delete_worktree(ctx, current_worktree)
    pull_branch(ctx)  # Even if this fails, handler has valid script
```

### Commands Using This Pattern

| Command               | Destructive Operations                  |
| --------------------- | --------------------------------------- |
| `pr land`             | Deletes worktree, deletes branch, pulls |
| `wt delete`           | Deletes current worktree                |
| `checkout` (deleting) | Deletes old worktree when switching     |
| `down --delete`       | Deletes current and moves down stack    |

## Handler Failure Recovery

The handler in `src/erk/cli/shell_integration/handler.py` implements graceful degradation:

```
Command Output → Handler Checks → Result
────────────────────────────────────────
Script path exists → Use script (even if exit_code != 0)
No script + exit_code != 0 → Passthrough (re-run command)
No script + exit_code == 0 → No-op (command succeeded, no cd needed)
```

### Implications for Command Design

1. **Script enables partial success**: If your command outputs a script early and later steps fail, the shell can still navigate to the destination directory.

2. **Forward stderr on failure**: The handler outputs stderr when using a script with non-zero exit:

   ```python
   if exit_code != 0 and stderr:
       user_output(stderr, nl=False)
   ```

3. **Passthrough for help/dry-run**: Commands with `--help`, `--script`, or `--dry-run` flags passthrough directly—the handler doesn't inject `--script`.

## Testing Pattern

Test that scripts are output before failures:

```python
def test_script_output_before_failure() -> None:
    """Script should exist even when later operations fail."""
    # Setup: mock pull to fail
    ctx.git.pull_branch = Mock(side_effect=GitError("fetch failed"))

    result = runner.invoke(pr_land, ["--script"], obj=ctx)

    # Script was written before the failure
    assert result.exit_code != 0
    script_path = result.output.strip()
    assert Path(script_path).exists()
    assert "cd" in Path(script_path).read_text()
```

## Related Documentation

- [Shell Integration Constraint](shell-integration-constraint.md) — Why subprocesses can't change parent shell cwd
- [Script Mode](../cli/script-mode.md) — Implementing the `--script` flag pattern
