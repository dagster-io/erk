---
title: Claude CLI Integration from Python
read_when:
  - Invoking Claude from Python
  - Spawning Claude CLI from Python code
  - Understanding non-interactive vs interactive modes
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

## Reference Implementation

See `packages/erk-kits/src/erk_kits/data/kits/command/kit_cli_commands/command/ops.py`:

- `RealClaudeCliOps`: Production implementation with streaming output
- `FakeClaudeCliOps`: Test double for unit testing
