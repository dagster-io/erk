# Fix PR Land Buffering and Extraction Plan URL

## Problem Summary

Two issues with `erk pr land`:

1. **Live feedback not working**: Status messages ("Getting current branch...", etc.) all appear at once after the operation completes instead of streaming in real-time
2. **Missing extraction plan link**: The URL for the created extraction plan is not shown in the output

## Root Cause Analysis

### Issue 1: Live Feedback Buffering

**Root Cause**: The shell integration handler (`src/erk/cli/shell_integration/handler.py`) uses Click's `CliRunner()` to invoke commands (lines 163-169):

```python
runner = CliRunner()
result = runner.invoke(command, script_args, ...)
```

**CliRunner captures ALL output** (both stdout and stderr) in memory until the command completes. Only after completion does the handler output stderr via `user_output(stderr, nl=False)` (line 110).

The `sys.stderr.flush()` in `render_events()` has no effect because CliRunner intercepts stderr before it reaches the terminal.

### Issue 2: Missing Extraction Plan URL

**Root Cause**: `run_claude_extraction_plan()` in `src/erk/core/shell.py` (lines 179-196):

```python
result = subprocess.run(cmd, capture_output=True, ...)
try:
    data = json.loads(result.stdout)
    issue_url = data.get("issue_url")
```

Claude CLI with `--print` mode outputs conversation/thinking text before the final JSON. The JSON parsing likely fails because `result.stdout` isn't pure JSON.

## Solution

### Fix 1: Replace CliRunner with Subprocess for Live Streaming

Modify `_invoke_hidden_command()` in `handler.py` to use `subprocess.Popen` instead of CliRunner:

1. Run `command erk <command> --script` as a subprocess
2. Let stderr pass through directly to terminal (live streaming)
3. Capture only stdout (for the activation script path)

```python
def _invoke_hidden_command(command_name: str, args: tuple[str, ...]) -> ShellIntegrationResult:
    # ... existing help/passthrough checks ...

    # Build full command with --script flag
    cmd = ["erk", *command_name.split(), *args, "--script"]

    # Run subprocess: stderr goes to terminal (live), stdout captured for script path
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,  # Capture stdout for script path
        stderr=None,              # Let stderr pass through to terminal
        text=True,
    )

    script_path = result.stdout.strip() if result.stdout else None
    # ... rest of processing ...
```

### Fix 2: Extract JSON from Claude Output

Modify `run_claude_extraction_plan()` in `shell.py` to find the JSON in the output:

```python
def run_claude_extraction_plan(self, cwd: Path) -> str | None:
    # ... run command ...

    # Find JSON in output (may have non-JSON text before it)
    for line in reversed(result.stdout.strip().split('\n')):
        try:
            data = json.loads(line)
            if isinstance(data, dict) and "issue_url" in data:
                issue_url = data.get("issue_url")
                if isinstance(issue_url, str):
                    return issue_url
        except json.JSONDecodeError:
            continue
    return None
```

## Files to Modify

1. **`src/erk/cli/shell_integration/handler.py`** - Replace CliRunner with subprocess.run for live stderr streaming
2. **`src/erk/core/shell.py`** - Improve JSON extraction from Claude output
3. **`tests/fakes/shell.py`** - Update FakeShell if interface changes
4. **`tests/unit/shell_integration/test_handler_commands.py`** - Update tests for new subprocess approach

## Testing Strategy

1. Manual test: Run `erk pr land` and verify progress messages appear in real-time
2. Manual test: Verify extraction plan URL appears in output
3. Unit tests: Update handler tests to verify subprocess invocation
4. Unit tests: Test JSON extraction with mixed output content

## Related Documentation

- Skills to load: `dignified-python-312`, `fake-driven-testing`
- Architecture doc: `docs/agent/architecture/shell-integration-patterns.md`