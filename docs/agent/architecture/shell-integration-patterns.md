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

## CliRunner Output Buffering

**Critical limitation:** Click's `CliRunner` buffers ALL output (both stdout and stderr) in memory until the command completes. This means:

- `sys.stderr.flush()` has no effect - output still waits for command completion
- Progress messages written to stderr won't appear in real-time
- Users see all status messages at once after the operation finishes

### Why This Matters

The shell integration handler in `handler.py` uses CliRunner to invoke commands with `--script`:

```python
runner = CliRunner()
result = runner.invoke(command, script_args, ...)
# ALL output is captured here - not streamed
```

Even if the command uses `click.echo(..., err=True)` with `sys.stderr.flush()`, the output is intercepted by CliRunner before reaching the terminal.

### When This Causes Problems

Commands with long-running operations that emit progress feedback:

- `pr land` - Multiple steps (merge PR, create extraction plan, delete worktree)
- `implement` - Claude CLI invocation with streaming output
- Any command with status spinners or progress indicators

## Live Output with Subprocess

When commands need real-time terminal output during shell integration, replace CliRunner with `subprocess.run()`:

### Pattern: stderr Passthrough

```python
def _invoke_with_live_output(command_name: str, args: tuple[str, ...]) -> ShellIntegrationResult:
    # Build command with --script flag
    cmd = ["erk", *command_name.split(), *args, "--script"]

    # stderr=None passes through to terminal (live output)
    # stdout=PIPE captures the script path
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,  # Capture for script path
        stderr=None,              # Passthrough for live feedback
        text=True,
    )

    script_path = result.stdout.strip() if result.stdout else None
    return process_command_result(result.returncode, script_path, None, command_name)
```

### Key Differences from CliRunner

| Aspect            | CliRunner                   | subprocess.run()           |
| ----------------- | --------------------------- | -------------------------- |
| stderr            | Captured in `result.stderr` | Passes through to terminal |
| stdout            | Captured in `result.stdout` | Captured if `stdout=PIPE`  |
| Live feedback     | No (buffered)               | Yes (stderr streams)       |
| Context injection | Uses Click's `obj=`         | Uses environment/CLI args  |

### Trade-offs

**subprocess.run() advantages:**

- Real-time stderr output to terminal
- Users see progress as it happens

**subprocess.run() disadvantages:**

- No access to stderr content for error handling
- Must construct full CLI command (no direct function invocation)
- Context must be passed via environment or CLI flags

## Related Documentation

- [Shell Integration Constraint](shell-integration-constraint.md) — Why subprocesses can't change parent shell cwd
- [Script Mode](../cli/script-mode.md) — Implementing the `--script` flag pattern
