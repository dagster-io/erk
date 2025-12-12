---
title: Claude CLI Integration from Python
read_when:
  - Invoking Claude from Python
  - Spawning Claude CLI from Python code
  - Understanding non-interactive vs interactive modes
  - Passing large prompts to Claude CLI
  - Avoiding argument list too long errors
tripwires:
  - action: "passing prompt as command-line argument to Claude CLI"
    warning: "Use input= parameter for stdin to avoid OSError with large prompts."
---

# Claude CLI Integration from Python

## Overview

When erk CLI commands need Claude AI capabilities (analysis, generation, etc.), they can spawn Claude Code CLI as a subprocess. This document covers the patterns for doing so.

## Input Methods

The Claude CLI accepts prompts via two methods:

### Command-line Argument (Limited)

```python
subprocess.run(["claude", "--print", "Your prompt here"], ...)
```

- Subject to OS argument list size limit (~128KB on Linux/macOS)
- Will fail with `OSError: [Errno 7] Argument list too long` for large prompts
- Acceptable only for short, fixed prompts

### Stdin (Preferred for Variable-Size Prompts)

```python
subprocess.run(
    ["claude", "--print", "--model", model],
    input=prompt,  # Pass via stdin, not as argument
    capture_output=True,
    text=True,
)
```

- No size limit (stdin is not subject to kernel arg limits)
- **Preferred** for subprocess invocation with variable-size prompts
- Required when prompt size cannot be guaranteed small

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

## Key Flags

| Flag                             | Purpose                                             |
| -------------------------------- | --------------------------------------------------- |
| `--print`                        | Non-interactive mode, print response and exit       |
| `--model <name>`                 | Model selection (e.g., "haiku", "sonnet", "opus")   |
| `--dangerously-skip-permissions` | Bypass permission prompts (for automation)          |
| `--output-format json`           | Structured JSON output                              |
| `--verbose`                      | Required with `--print --output-format stream-json` |

## Reference Implementation

See `packages/dot-agent-kit/src/dot_agent_kit/data/kits/command/kit_cli_commands/command/ops.py`:

- `RealClaudeCliOps`: Production implementation with streaming output
- `FakeClaudeCliOps`: Test double for unit testing

For robust prompt passing, see `packages/erk-shared/src/erk_shared/prompt_executor/real.py` which demonstrates the stdin pattern to avoid argument list size limits.
