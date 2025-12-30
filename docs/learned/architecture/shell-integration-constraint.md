---
title: Shell Integration Constraint
read_when:
  - "implementing commands that delete the current worktree"
  - "debugging directory change issues after worktree operations"
  - "understanding why safe_chdir doesn't work for some commands"
---

# Shell Integration Constraint

## The Fundamental Limitation

A subprocess cannot change its parent shell's current working directory.

This is a Unix process model constraint: each process has its own cwd that is isolated from its parent. When erk runs as a subprocess of the shell, any `os.chdir()` or `safe_chdir()` calls only affect erk's process, not the parent shell.

## Why This Matters

Commands that delete the current worktree leave the user's shell stranded in a deleted directory:

```bash
# User is in ~/erks/erk/my-feature/
$ erk pr land
# Worktree deleted, PR landed
# But shell is still in the deleted directory!
$ pwd
/Users/you/erks/erk/my-feature  # Still here, but directory is gone
$ ls
ls: .: No such file or directory
```

## safe_chdir() Doesn't Help

The `safe_chdir()` function changes the Python process's cwd, but this doesn't propagate to the parent shell:

```python
# This changes erk's cwd, not the user's shell cwd
safe_chdir(new_path)  # Only affects the subprocess
# When erk exits, the shell is still in the old (deleted) directory
```

## Commands Requiring Shell Integration

These commands MUST use shell integration (the `--script` flag pattern):

| Command                 | Why                                           |
| ----------------------- | --------------------------------------------- |
| `pr land`               | Deletes current worktree after landing PR     |
| `down --delete-current` | Deletes current worktree and moves down stack |
| `up --delete-current`   | Deletes current worktree and moves up stack   |
| `rm` (when in worktree) | Deletes the current worktree                  |

## Implementation Pattern: Fail-Fast Validation

Commands that delete the current worktree should fail-fast if shell integration is not active:

```python
@click.command()
@click.option("--script", is_flag=True, hidden=True)
@click.pass_obj
def land(ctx: ErkContext, script: bool) -> None:
    """Land PR and delete worktree."""
    # Check if we're in a worktree that will be deleted
    if is_current_worktree(ctx):
        if not script:
            # Fail-fast: user needs shell integration
            raise click.ClickException(
                "This command deletes the current worktree.\n"
                "Use the shell wrapper function: erk pr land\n"
                "Or with explicit script mode: source <(erk pr land --script)"
            )

    # Proceed with operation...
```

## How Shell Integration Works

1. **User invokes command via shell wrapper**: `erk pr land`
2. **Wrapper detects shell integration is needed**: Command deletes current directory
3. **Wrapper runs with --script**: `source <(erk pr land --script)`
4. **Command outputs activation script path**: Script includes `cd` to new location
5. **Shell sources the script**: Parent shell's cwd changes correctly

```bash
# The shell wrapper function (in ~/.erk/shell/init.zsh or init.bash)
erk() {
    # For commands that need shell integration, use source pattern
    local result
    result=$("$ERK_BIN" "$@" --script 2>&1)
    if [[ -f "$result" ]]; then
        source "$result"
    else
        # Just run normally
        "$ERK_BIN" "$@"
    fi
}
```

## Testing Considerations

When testing commands that require shell integration:

1. **Test the fail-fast behavior**: Verify command fails without `--script`
2. **Test script output**: Verify `--script` produces valid shell script path
3. **Test the script content**: Verify script changes to correct directory

```python
def test_land_fails_without_script_in_current_worktree() -> None:
    """Land should fail-fast when in current worktree without --script."""
    result = runner.invoke(land, [], obj=ctx_in_worktree)
    assert result.exit_code != 0
    assert "shell wrapper" in result.output.lower()

def test_land_outputs_script_path_with_script_flag() -> None:
    """Land with --script should output activation script path."""
    result = runner.invoke(land, ["--script"], obj=ctx_in_worktree)
    assert result.exit_code == 0
    assert "erk-activation-scripts/" in result.output
```

## Common Mistakes

### ❌ Trying to use safe_chdir() to "escape"

```python
# This doesn't work - only changes subprocess cwd
safe_chdir(escape_path)
delete_worktree(current_worktree)
# User's shell is still stranded
```

### ❌ Assuming directory exists after deletion

```python
delete_worktree(current_worktree)
# DON'T assume operations in the old directory work
os.listdir(".")  # Fails if we were in the deleted worktree
```

### ✅ Correct: Require shell integration for destructive operations

```python
if not script:
    raise click.ClickException(
        "Use shell wrapper for this command: erk pr land"
    )
# With --script, output activation script that handles cd
```

## Related Documentation

- [Script Mode](../cli/script-mode.md) - Implementing `--script` flag pattern
- [Shell Aliases](../cli/shell-aliases.md) - When aliases bypass shell integration
- [Glossary: Shell Integration](../glossary.md#shell-integration) - Definition and setup
