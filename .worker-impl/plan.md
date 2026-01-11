# Documentation Plan: TUI Subprocess stdin Deadlock Prevention

## Context

This plan addresses documentation gaps discovered while fixing issue #4730 (erk dash hangs when landing PR with unresolved comments).

### Root Cause Summary

When `erk dash` TUI executes commands via `subprocess.Popen()`, the child process inherits stdin from the parent TUI. If the child process attempts to prompt for user input (e.g., `click.confirm()` for unresolved PR comments), it creates a deadlock:

1. TUI manages terminal input via Textual event loop
2. Child process tries to read from inherited stdin (connected to same TTY)
3. Neither can proceed → permanent hang showing "Running..."

### Fix Applied

Added `stdin=subprocess.DEVNULL` to `plan_detail_screen.py:507`:

```python
process = subprocess.Popen(
    command,
    cwd=cwd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL,  # Prevents deadlock
    text=True,
    bufsize=1,
)
```

### Key Files

- `src/erk/tui/screens/plan_detail_screen.py` - Where the fix was applied
- `src/erk/cli/commands/land_cmd.py:188-194` - Where confirmation prompt occurs
- `docs/learned/tui/command-execution.md` - Current docs (missing stdin guidance)

## Raw Materials

https://gist.github.com/schrockn/c2488a71eb0852f4b2e80177779b78f1

## Documentation Items

### Item 1: Update command-execution.md

**Location:** `docs/learned/tui/command-execution.md`
**Action:** Update
**Source:** [Plan] - Root cause discovery

The current streaming subprocess example (lines 95-108) shows `Popen` without stdin handling. Update to include the safeguard:

```python
def execute_streaming(
    command: list[str],
    cwd: str,
    on_output: Callable[[str], None]
) -> int:
    """Execute command with streaming output.

    Args:
        command: Command and arguments
        cwd: Working directory
        on_output: Callback for each line of output

    Returns:
        Exit code
    """
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,  # CRITICAL: Prevents deadlock if child prompts
        text=True,
        bufsize=1
    )

    assert process.stdout is not None
    for line in process.stdout:
        on_output(line.rstrip())

    return process.wait()
```

Also add a "Gotchas" or "Common Pitfalls" section explaining why stdin handling matters in TUI context.

### Item 2: Add Tripwire

**Location:** `docs/learned/tripwires.md`
**Action:** Update (add new tripwire)
**Source:** [Plan] - Root cause discovery

Add tripwire in the appropriate location (likely near other subprocess-related tripwires):

```markdown
**CRITICAL: Before using subprocess.Popen in TUI code without stdin=subprocess.DEVNULL** → Read [Command Execution Strategies](tui/command-execution.md) first. Child processes inherit stdin from parent; in TUI context this creates deadlocks when child prompts for user input. Always set `stdin=subprocess.DEVNULL` for TUI subprocess calls.
```

### Item 3: Update tripwires.md frontmatter

**Location:** `docs/learned/tripwires.md` frontmatter
**Action:** Update
**Source:** Implementation requirement

Ensure the new tripwire is properly formatted in the frontmatter so `erk docs sync` generates it correctly.