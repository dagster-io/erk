---
title: CLI Script Mode
read_when:
  - "implementing script mode"
  - "suppressing diagnostic output"
  - "integrating with shell handlers"
  - "debugging shell integration"
  - "global flag handling in shell integration"
  - "shell integration handler not recognizing commands"
  - "adding a command with --script flag"
tripwires:
  - action: "adding a command with --script flag"
    warning: "Must register in SHELL_INTEGRATION_COMMANDS with all alias variants (e.g., br land, branch land)."
---

# CLI Script Mode

## Overview

Script mode is a command flag (`--script`) that suppresses diagnostic output to keep stdout clean for programmatic parsing by the shell integration handler.

## Motivation

Shell integration allows commands to automatically activate worktrees and switch directories. For this to work, the shell must:

1. Execute a command with `--script` flag: `source <(erk implement 123 --script)`
2. Parse the command's stdout to find the activation script path
3. Source the activation script to change directory and set environment

This requires **clean stdout** - any diagnostic output would break parsing.

## The Problem: Mixed Output

Without script mode, commands produce mixed output:

```bash
$ erk implement 123
Fetching issue from GitHub...
Issue: Add Authentication Feature
Creating worktree 'add-authentication-feature'...
✓ Created worktree: add-authentication-feature
✓ Saved issue reference for PR linking

Next steps:
  1. Change to worktree:  erk br co add-authentication-feature
  2. Run implementation:  claude --permission-mode acceptEdits "/erk:system:impl-execute"
```

The shell integration handler can't parse this - it needs only the script path.

## The Solution: UserFeedback Abstraction

The `UserFeedback` abstraction eliminates threading `script` booleans through function signatures. Instead, functions call `ctx.feedback` methods which automatically handle output suppression based on the current mode.

### Two Implementations

**InteractiveFeedback** (default, `script=False`):

- `info()` → outputs to stderr
- `success()` → outputs to stderr with green styling
- `error()` → outputs to stderr with red styling

**SuppressedFeedback** (`script=True`):

- `info()` → suppressed
- `success()` → suppressed
- `error()` → still outputs to stderr (errors always surface)

### Activation Script Output

Commands still output activation scripts via `user_output()`:

```python
# Diagnostic output (suppressed in script mode)
ctx.feedback.info("Creating worktree...")
ctx.feedback.success("✓ Created worktree")

# Activation script (always output)
if script:
    script_content = render_activation_script(...)
    result = ctx.script_writer.write_activation_script(...)
    result.output_for_shell_integration()  # Prints script path to stdout
```

## Implementation Pattern

### 1. Add --script Flag

```python
@click.command("implement")
@click.option(
    "--script",
    is_flag=True,
    hidden=True,  # Hide from --help (internal use)
    help="Output activation script for shell integration",
)
@click.pass_obj
def implement(
    ctx: ErkContext,
    target: str,
    script: bool,
) -> None:
    """Create worktree from GitHub issue or plan file."""
    # Implementation...
```

### 2. Use ctx.feedback for Diagnostics

Replace direct `user_output()` calls with `ctx.feedback` methods:

```python
# ❌ BAD: Direct output (always visible)
user_output("Fetching issue from GitHub...")
user_output(click.style("✓ Created worktree", fg="green"))

# ✅ GOOD: Mode-aware output (suppressed in script mode)
ctx.feedback.info("Fetching issue from GitHub...")
ctx.feedback.success("✓ Created worktree")
```

### 3. Provide Two Output Modes

```python
if script:
    # Output activation script for shell integration
    script_content = render_activation_script(
        worktree_path=wt_path,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="implement activation",
    )
    result = ctx.script_writer.write_activation_script(
        script_content,
        command_name="implement",
        comment=f"activate {wt_path.name}",
    )
    result.output_for_shell_integration()
else:
    # Provide manual instructions
    user_output("\n" + click.style("Next steps:", fg="cyan", bold=True))
    user_output(f"  1. Change to worktree:  erk br co {branch}")
    user_output(f"  2. Run implementation:  claude ...")
```

### 4. Inject Correct Feedback Implementation

Context construction handles this automatically:

```python
# In ErkContext creation (src/erk/core/context.py)
feedback = (
    SuppressedFeedback() if script else InteractiveFeedback()
)

ctx = ErkContext(
    feedback=feedback,
    # ... other dependencies
)
```

## Example: implement Command

### Without --script (Interactive Mode)

```bash
$ erk implement 123
Fetching issue from GitHub...
Issue: Add Authentication Feature
Creating worktree 'add-authentication-feature'...
Running erk br co...
✓ Created worktree: add-authentication-feature
✓ Saved issue reference for PR linking

Next steps:
  1. Change to worktree:  erk br co add-authentication-feature
  2. Run implementation:  claude --permission-mode acceptEdits "/erk:system:impl-execute"

Shell integration not detected.
To activate environment and run implementation, use:
  source <(erk implement 123 --script)
```

### With --script (Script Mode)

```bash
$ erk implement 123 --script
$TMPDIR/erk-activation-scripts/implement-20250123-142530.sh
```

Clean stdout with only the script path - perfect for shell integration.

## Testing Guidance

### Testing with FakeUserFeedback

The `FakeUserFeedback` fake both captures messages and outputs them so `CliRunner` can capture them:

```python
def test_implement_from_issue() -> None:
    """Test implementing from GitHub issue number."""
    # Arrange
    git = FakeGit(...)
    store, _ = create_plan_store_with_plans({"42": plan})
    ctx = build_workspace_test_context(env, git=git, plan_store=store)

    # Act
    result = runner.invoke(implement, ["#42"], obj=ctx)

    # Assert: Check CLI output (captured by CliRunner)
    assert result.exit_code == 0
    assert "Created worktree" in result.output  # From ctx.feedback.success()
    assert "Next steps:" in result.output       # From user_output()

    # Could also assert on captured messages if needed
    # assert "INFO: Fetching issue" in ctx.feedback.messages
```

### Testing Script Mode

```python
def test_implement_outputs_script_path_in_script_mode() -> None:
    """Test that --script flag outputs only the script path."""
    # Arrange
    git = FakeGit(...)
    ctx = build_workspace_test_context(env, git=git)

    # Act
    result = runner.invoke(implement, ["#42", "--script"], obj=ctx)

    # Assert: Only script path in output, no diagnostics
    assert result.exit_code == 0
    assert "erk-activation-scripts/" in result.output
    assert "Fetching issue" not in result.output
    assert "Created worktree" not in result.output
```

## When to Use Script Mode

Add `--script` flag support to commands that:

1. **Create worktrees** (implement, create)
2. **Switch directories** (checkout, switch)
3. **Need shell integration** for automatic activation

Don't add script mode to:

- Read-only commands (status, list, tree)
- Commands with no directory changes
- Commands that don't benefit from shell integration

## Required vs Optional Script Mode

Script mode is **required** (not optional) for commands that delete the current worktree.

### Optional Script Mode

For most commands, script mode is a convenience - it enables automatic directory switching. Without it, users can manually run `cd` or `erk br co`:

```bash
# Without shell integration - still works, just requires manual cd
$ erk create my-feature
Created worktree: my-feature
$ cd ~/erks/erk/my-feature  # Manual step

# With shell integration - automatic cd
$ erk create my-feature
# Already in ~/erks/erk/my-feature
```

### Required Script Mode

For commands that **delete the current worktree**, script mode is mandatory. Without it, the shell gets stranded in a deleted directory:

| Command                     | Why Required                         |
| --------------------------- | ------------------------------------ |
| `erk pr land`               | Deletes worktree after landing PR    |
| `erk down --delete-current` | Deletes current worktree, moves down |
| `erk up --delete-current`   | Deletes current worktree, moves up   |
| `erk rm` (in worktree)      | Deletes the current worktree         |

### Implementation: Fail-Fast Without --script

Commands requiring script mode should fail early with a helpful error:

```python
@click.command()
@click.option("--script", is_flag=True, hidden=True)
@click.pass_obj
def land(ctx: ErkContext, script: bool) -> None:
    """Land PR and delete worktree."""
    if is_in_current_worktree(ctx) and not script:
        raise click.ClickException(
            "This command deletes the current worktree.\n\n"
            "Use the shell wrapper: erk pr land\n"
            "Or explicitly: source <(erk pr land --script)\n\n"
            "See: erk init --shell"
        )
    # ... proceed with operation
```

**Why fail-fast?** Running without shell integration would "succeed" (PR lands, worktree deleted) but leave the user stranded. It's better to fail early with a clear message than to succeed and create a confusing state.

### Cross-Reference

For the underlying reason why this is necessary, see [Shell Integration Constraint](../architecture/shell-integration-constraint.md) - subprocesses cannot change parent shell cwd.

## Shell Integration Flow

1. User runs command with shell wrapper: `erk implement 123`
2. Wrapper checks if shell integration is active
3. If active, wrapper runs: `source <(erk implement 123 --script)`
4. Command with `--script`:
   - Suppresses diagnostics via `SuppressedFeedback`
   - Writes activation script to temp file
   - Outputs only script path to stdout
5. Shell sources the script, activating worktree

## Shell Integration Handler: Global Flag Handling

The shell integration handler (`src/erk/cli/shell_integration/handler.py`) must strip global CLI flags before matching commands against `SHELL_INTEGRATION_COMMANDS`.

### The Problem

When users run commands with global flags like `--debug`, the shell wrapper passes args that include these flags:

```bash
$ erk --debug pr land
# Shell wrapper receives: ('--debug', 'pr', 'land')
```

Without stripping global flags, the handler tries to match `"--debug pr"` as a compound command, which fails:

1. First tries compound: `"--debug pr"` → not in `SHELL_INTEGRATION_COMMANDS`
2. Falls back to single: `"--debug"` → not in `SHELL_INTEGRATION_COMMANDS`
3. Returns passthrough (no `--script` flag added)
4. Command runs without shell integration
5. User sees misleading "requires shell integration" error

### The Solution

Strip known global flags from the beginning of args before command matching:

```python
GLOBAL_FLAGS: Final[set[str]] = {"--debug", "--dry-run", "--verbose", "-v"}

def handle_shell_request(args: tuple[str, ...]) -> ShellIntegrationResult:
    """Dispatch shell integration handling based on the original CLI invocation."""
    if len(args) == 0:
        return ShellIntegrationResult(passthrough=True, script=None, exit_code=0)

    # Strip global flags from beginning of args
    args_list = list(args)
    while args_list and args_list[0] in GLOBAL_FLAGS:
        args_list.pop(0)

    # Now match commands without the global flags
    if len(args_list) >= 2:
        compound_name = f"{args_list[0]} {args_list[1]}"
        if compound_name in SHELL_INTEGRATION_COMMANDS:
            return _invoke_hidden_command(compound_name, tuple(args_list[2:]))

    # Fall back to single command
    command_name = args_list[0]
    command_args = args_list[1:] if len(args_list) > 1 else ()
    return _invoke_hidden_command(command_name, command_args)
```

### Why This Matters

Global flags are Click's responsibility to parse, not the handler's. The handler only needs to:

1. Identify which command to invoke (requires stripping global flags)
2. Pass all args (including global flags) to the command with `--script` added

The command itself will parse global flags via Click's normal option handling.

## Debugging Shell Integration

When shell integration isn't working as expected, use these debugging techniques:

### Test the Shell Handler Directly

```bash
# Test what the shell handler receives and returns
ERK_SHELL=zsh command erk __shell pr land

# With debug output
ERK_DEBUG=1 ERK_SHELL=zsh command erk __shell pr land
```

### Interpreting Handler Output

- `__ERK_PASSTHROUGH__` output means command matching failed
- Exit code 0 + passthrough = handler didn't recognize the command
- Exit code 1 + passthrough = handler invoked command but it failed
- Script path output = successful shell integration activation

### Common Issues

**Problem: Command shows "requires shell integration" error**

This usually means:

1. The handler returned passthrough (check for `__ERK_PASSTHROUGH__`)
2. Command ran without `--script` flag
3. Command detected it needed shell integration and failed

**Debug steps:**

1. Run with `ERK_DEBUG=1` to see handler decisions
2. Check if global flags are preventing command match
3. Verify command is in `SHELL_INTEGRATION_COMMANDS` dict
4. Check `handle_shell_request()` logic for why passthrough occurred

**Problem: Global flags cause passthrough**

```bash
# This might fail if handler doesn't strip --debug
$ erk --debug pr land
Error: This command requires shell integration
```

**Solution:** Ensure `GLOBAL_FLAGS` includes the flag and `handle_shell_request()` strips it before matching.

## Adding New Shell-Integrated Commands

When creating a command that uses shell integration (`--script` flag for directory switching), you MUST register it in `SHELL_INTEGRATION_COMMANDS` in `src/erk/cli/shell_integration/handler.py`.

### Checklist

1. Add `--script` flag to your command
2. Register in `SHELL_INTEGRATION_COMMANDS` dict with **all alias variants**:
   - Group aliases (e.g., `br` for `branch`)
   - Command aliases (e.g., `co` for `checkout`)
   - All combinations (e.g., `br co`, `br checkout`, `branch co`, `branch checkout`)

### Example

For `branch checkout` with aliases `br` (group) and `co` (command):

```python
SHELL_INTEGRATION_COMMANDS = {
    # ... existing entries ...
    "branch checkout": ["branch", "checkout"],
    "branch co": ["branch", "checkout"],
    "br checkout": ["branch", "checkout"],
    "br co": ["branch", "checkout"],
}
```

### Symptom if Missed

Users see "Shell integration not detected" even with shell wrapper installed.

## Related Files

- `src/erk/core/user_feedback.py` - UserFeedback abstraction and implementations
- `tests/fakes/user_feedback.py` - FakeUserFeedback for testing
- `src/erk/cli/commands/implement.py` - Example command with script mode
- `src/erk/cli/activation.py` - Activation script rendering

## See Also

- [output-styling.md](output-styling.md) - CLI output formatting guidelines
- [Command Agent Delegation](../planning/agent-delegation.md) - Delegating to agents from commands
