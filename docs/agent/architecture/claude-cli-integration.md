---
title: Claude CLI Integration from Python
read_when:
  - "invoking Claude Code CLI from Python"
  - "spawning Claude agents from CLI commands"
  - "understanding Claude subprocess patterns"
---

# Claude CLI Integration from Python

## Overview

When erk CLI commands need Claude AI capabilities (analysis, generation, reasoning), they can spawn Claude Code CLI as a subprocess. This document covers patterns for doing so effectively.

## When to Spawn Claude CLI

Use this pattern when:

- Your Python CLI command needs AI analysis (e.g., categorizing documentation gaps)
- The operation requires Claude's reasoning capabilities
- You want to reuse existing agent commands from Python code
- Natural language understanding or generation is required

Do NOT use this pattern when:

- Pure Python logic suffices (parsing, file operations, git commands)
- You're already inside a Claude Code session (use tools directly)
- The operation is deterministic (same input always produces same output)

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

### Key Flags

- `--print`: Non-interactive mode, runs command and exits
- `--verbose`: Required for stream-json output with --print
- `--permission-mode bypassPermissions`: Skip permission prompts (use for automation)
- `--output-format stream-json`: Structured JSONL output for parsing

### When to Use Non-Interactive Mode

- Automated workflows (CI, scheduled tasks)
- Background processing
- Commands that produce structured output
- Operations requiring no user input

## Interactive Mode

For operations requiring user input during execution:

```python
import subprocess

result = subprocess.run(
    ["claude", "/erk:my-command"],
    cwd=working_directory,
)

if result.returncode != 0:
    raise SystemExit(1)
```

### When to Use Interactive Mode

- User needs to make selections during execution
- Confirmation prompts are required
- The agent command has multi-step user interaction
- Real-time feedback is important

## Reference Implementation

See the command kit for a complete implementation:

**Location**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/command/kit_cli_commands/command/ops.py`

Key components:

- `RealClaudeCliOps`: Production implementation with streaming output
- `FakeClaudeCliOps`: Test double for unit testing
- `ClaudeCliOps`: ABC interface for dependency injection

### Example: Using the Kit Pattern

```python
from dataclasses import dataclass
from dot_agent_kit.kits.command.ops import ClaudeCliOps

@dataclass
class Service:
    claude_ops: ClaudeCliOps

    def analyze_sessions(self) -> None:
        """Spawn Claude to analyze sessions."""
        self.claude_ops.execute_command(
            command="/erk:analyze-sessions",
            working_dir=self.repo_root,
        )
```

## Error Handling

Always check the return code and handle failures appropriately:

```python
from erk.cli.subprocess_utils import run_with_error_reporting

# CLI layer: User-friendly error + SystemExit
run_with_error_reporting(
    ["claude", "--print", "--verbose", "/erk:my-command"],
    operation_context="run Claude analysis",
    cwd=repo_root,
)
```

Or for business logic:

```python
from erk.core.subprocess import run_subprocess_with_context

# Integration layer: Raises RuntimeError with rich context
result = run_subprocess_with_context(
    ["claude", "--print", "--verbose", "/erk:my-command"],
    operation_context="execute Claude command for analysis",
    cwd=repo_root,
)
```

See [Subprocess Wrappers](subprocess-wrappers.md) for complete guidance on subprocess execution patterns.

## Working Directory

Always set `cwd` parameter to ensure Claude operates in the correct context:

```python
# ✅ CORRECT: Explicit working directory
subprocess.run(
    ["claude", "/erk:my-command"],
    cwd=repo_root,
)

# ❌ WRONG: Implicit working directory (may not be repo root)
subprocess.run(["claude", "/erk:my-command"])
```

## Complete Example

```python
from pathlib import Path
import subprocess
from erk.core.subprocess import run_subprocess_with_context

def create_extraction_plan(repo_root: Path, session_ids: list[str]) -> None:
    """Create documentation extraction plan by spawning Claude."""
    # Build command with session IDs
    cmd = [
        "claude",
        "--print",
        "--verbose",
        "--permission-mode", "bypassPermissions",
        f"/erk:create-extraction-plan {' '.join(session_ids)}",
    ]

    # Execute with proper error handling
    run_subprocess_with_context(
        cmd,
        operation_context="create extraction plan from sessions",
        cwd=repo_root,
    )
```

## Testing

When testing code that spawns Claude CLI, use dependency injection with fakes:

```python
# Test with fake
def test_analyze_sessions():
    fake_claude = FakeClaudeCliOps()
    service = Service(claude_ops=fake_claude)

    service.analyze_sessions()

    assert fake_claude.executed_command == "/erk:analyze-sessions"
```

## Related Topics

- [Subprocess Wrappers](subprocess-wrappers.md) - Error handling patterns
- [Command Boundaries](command-boundaries.md) - When to use agent vs CLI commands
