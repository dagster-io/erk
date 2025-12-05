---
title: Claude CLI Integration from Python
read_when:
  - "spawning Claude CLI from Python"
  - "invoking agent commands programmatically"
  - "parsing JSONL stream output"
  - "implementing hybrid CLI + agent patterns"
---

# Claude CLI Integration from Python

## Overview

When erk CLI commands need Claude AI capabilities (analysis, generation, etc.), they can spawn Claude Code CLI as a subprocess. This document covers the patterns for doing so.

## When to Spawn Claude CLI

Use this pattern when:

- Your Python CLI command needs AI analysis (e.g., categorizing documentation gaps)
- The operation requires Claude's reasoning capabilities
- You want to reuse existing agent commands from Python code

Do NOT use this pattern when:

- Pure Python logic suffices (parsing, file operations, git commands)
- You're already inside a Claude Code session (use tools directly)

## Non-Interactive Mode (`--print`)

For automated/scripted execution where no user interaction is needed:

```python
import subprocess

result = subprocess.run(
    [
        "claude",
        "--print",
        "--verbose",
        "--permission-mode", "bypassPermissions",
        "--output-format", "stream-json",
        "/erk:my-command",
    ],
    cwd=working_directory,
)

if result.returncode != 0:
    # Handle failure
    raise SystemExit(1)
```

Key flags:

- `--print`: Non-interactive, runs command and exits
- `--verbose`: Required for stream-json with --print
- `--permission-mode bypassPermissions`: Skip permission prompts
- `--output-format stream-json`: JSONL output for parsing

## Interactive Mode

For operations requiring user input during execution:

```python
result = subprocess.run(
    ["claude", "/erk:my-command"],
    cwd=working_directory,
)
```

Use interactive mode when:

- User needs to make selections during execution
- Confirmation prompts are required
- The agent command has multi-step user interaction

## Streaming Output with JSONL Parsing

When using `--output-format stream-json`, Claude CLI outputs JSONL (one JSON object per line). This enables real-time output parsing:

```python
import json
import subprocess

process = subprocess.Popen(
    [
        "claude",
        "--print",
        "--verbose",
        "--permission-mode", "bypassPermissions",
        "--output-format", "stream-json",
        "/erk:my-command",
    ],
    cwd=cwd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,  # Line buffered
)

# Stream and parse output line by line
if process.stdout is not None:
    for line in process.stdout:
        try:
            msg = json.loads(line)
            msg_type = msg.get("type")

            if msg_type == "assistant":
                # Handle assistant text and tool use
                pass
            elif msg_type == "user":
                # Handle tool results
                pass
            elif msg_type == "result":
                # Handle final result with usage stats
                pass
        except json.JSONDecodeError:
            # Handle invalid JSON (shouldn't happen normally)
            print(f"[Warning: Invalid JSON]: {line}")

returncode = process.wait()
```

### JSONL Message Types

The stream-json format emits several message types:

1. **`assistant` messages**: Contains Claude's text responses and tool invocations
   - Extract text from `content` array items with `type: "text"`
   - Extract tool uses from `content` array items with `type: "tool_use"`

2. **`user` messages**: Contains tool results
   - Extract tool results from `content` array items with `type: "tool_result"`

3. **`result` messages**: Final completion message with usage statistics
   - Contains `stop_reason`, `usage` metrics, etc.

4. **`system` messages**: Internal metadata (usually can be ignored)

## Reference Implementation

See `packages/dot-agent-kit/src/dot_agent_kit/data/kits/command/kit_cli_commands/command/ops.py` for a production implementation:

- **`ClaudeCliOps`**: ABC interface defining the contract
- **`RealClaudeCliOps`**: Production implementation with streaming output and JSONL parsing
- **`FakeClaudeCliOps`**: Test double for unit testing

The real implementation demonstrates:

- Subprocess spawning with `Popen` for streaming
- Line-by-line JSONL parsing
- Tool use and result extraction
- Status spinner integration
- Proper error handling

## Configuration Options

### Setting Sources

Use `--setting-sources project` to restrict Claude to project-level settings:

```python
cmd = [
    "claude",
    "--print",
    "--verbose",
    "--permission-mode", "bypassPermissions",
    "--setting-sources", "project",  # Only use .claude/settings.json
    "--output-format", "stream-json",
    "/erk:my-command",
]
```

This ensures consistent behavior across different user environments.

### Permission Modes

- `bypassPermissions`: Skip all permission prompts (for automated execution)
- `acceptEdits`: Auto-accept file edits but prompt for other actions
- `prompt`: Default interactive mode (requires user confirmation)

Use `bypassPermissions` for non-interactive automation. Use `acceptEdits` when you trust the command but want visibility into other operations.

## Testing Strategy

When testing code that spawns Claude CLI:

1. **Use dependency injection**: Accept a `ClaudeCliOps` parameter
2. **Use the fake**: Pass `FakeClaudeCliOps()` in tests
3. **Verify executions**: Check that the fake recorded expected calls
4. **Configure behavior**: Use `set_next_returncode()` to simulate failures

Example:

```python
from dot_agent_kit.data.kits.command.kit_cli_commands.command.ops import (
    ClaudeCliOps,
    FakeClaudeCliOps,
)

def run_analysis(claude_ops: ClaudeCliOps, session_dir: Path) -> bool:
    result = claude_ops.execute_command(
        command_name="erk:analyze-session",
        cwd=session_dir,
        json_output=True,
    )
    return result.returncode == 0

# Test
def test_run_analysis():
    fake = FakeClaudeCliOps()
    fake.set_next_returncode(0)

    result = run_analysis(fake, Path("/tmp/session"))

    assert result is True
    assert fake.get_execution_count() == 1
    assert fake.get_last_execution() == ("erk:analyze-session", Path("/tmp/session"), True)
```

## Common Patterns

### Pattern 1: CLI Command Delegates to Agent

Python CLI handles validation and setup, then spawns agent for AI work:

```python
import subprocess
from pathlib import Path

def extract_documentation(session_id: str) -> int:
    """Extract documentation gaps from session (CLI command)."""
    # Python: Validate session exists
    session_dir = Path(f".erk/sessions/{session_id}")
    if not session_dir.exists():
        click.echo(f"Error: Session {session_id} not found", err=True)
        return 1

    # Agent: AI analysis
    result = subprocess.run(
        [
            "claude",
            "--print",
            "--verbose",
            "--permission-mode", "bypassPermissions",
            "--output-format", "stream-json",
            "/erk:analyze-session",
        ],
        cwd=session_dir,
    )

    return result.returncode
```

### Pattern 2: Hybrid with Result Processing

Agent generates structured output, CLI processes it:

```python
import json
import subprocess
from pathlib import Path

def create_and_publish_plan(issue_title: str) -> int:
    """Create plan with AI, then publish to GitHub (CLI command)."""
    # Agent: Generate plan
    result = subprocess.run(
        [
            "claude",
            "--print",
            "--verbose",
            "--permission-mode", "bypassPermissions",
            "--output-format", "stream-json",
            f"Create implementation plan for: {issue_title}",
        ],
        cwd=Path.cwd(),
    )

    if result.returncode != 0:
        return result.returncode

    # Python: Publish to GitHub
    plan_file = Path(".impl/plan.md")
    if not plan_file.exists():
        click.echo("Error: Agent did not create plan.md", err=True)
        return 1

    # Create GitHub issue via gh CLI
    subprocess.run(
        ["gh", "issue", "create", "--title", issue_title, "--body-file", str(plan_file)],
        check=True,
    )

    return 0
```

## Pitfalls to Avoid

### ❌ Don't use `shell=True`

```python
# BAD - Security risk
subprocess.run(f"claude /erk:my-command", shell=True)

# GOOD - Use list of arguments
subprocess.run(["claude", "/erk:my-command"])
```

### ❌ Don't forget `check=True` or returncode checking

```python
# BAD - Ignores failures
subprocess.run(["claude", "/erk:my-command"])

# GOOD - Check result
result = subprocess.run(["claude", "/erk:my-command"])
if result.returncode != 0:
    raise SystemExit(1)

# ALSO GOOD - Let exception propagate
subprocess.run(["claude", "/erk:my-command"], check=True)
```

### ❌ Don't spawn Claude from within Claude session

If your code is already running inside a Claude session (e.g., called from an agent command), use tools directly instead of spawning a subprocess.

### ❌ Don't use `--print` for interactive operations

If the command needs user input, omit `--print` and let Claude run in interactive mode.

## Related Documentation

- [Agent Command vs CLI Command Boundaries](command-boundaries.md) - When to use agent commands vs pure Python
- [Subprocess Wrappers](subprocess-wrappers.md) - Erk's two-layer subprocess abstraction pattern
