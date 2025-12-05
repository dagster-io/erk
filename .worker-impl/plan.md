## Objective

Add documentation about CliRunner output buffering limitations and the subprocess pattern for live terminal output in shell integration commands.

## Source Information

Session ID: abf7eba1-bb23-4aaa-bbb9-c07d53796e6a

## Documentation Items

### 1. CliRunner Output Buffering Limitation

**Type:** Category A (Learning Gap)
**Location:** docs/agent/architecture/shell-integration-patterns.md
**Action:** Update existing document
**Priority:** High (directly caused debugging time in this session)

**Content to add (new section):**

```markdown
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
```

---

### 2. Subprocess Pattern for Live Streaming

**Type:** Category B (Teaching Gap)
**Location:** docs/agent/architecture/shell-integration-patterns.md
**Action:** Update existing document
**Priority:** High (solution pattern for the buffering issue)

**Content to add (new section):**

```markdown
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

| Aspect | CliRunner | subprocess.run() |
|--------|-----------|------------------|
| stderr | Captured in `result.stderr` | Passes through to terminal |
| stdout | Captured in `result.stdout` | Captured if `stdout=PIPE` |
| Live feedback | No (buffered) | Yes (stderr streams) |
| Context injection | Uses Click's `obj=` | Uses environment/CLI args |

### Trade-offs

**subprocess.run() advantages:**
- Real-time stderr output to terminal
- Users see progress as it happens

**subprocess.run() disadvantages:**
- No access to stderr content for error handling
- Must construct full CLI command (no direct function invocation)
- Context must be passed via environment or CLI flags
```