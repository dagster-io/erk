---
title: Claude CLI Integration Patterns
read_when:
  - Passing prompts to Claude CLI
  - Subprocess invocation of Claude
  - Handling large prompts in Claude CLI calls
  - Avoiding OSError argument list too long
---

# Claude CLI Integration Patterns

This document covers patterns for invoking Claude CLI from erk code.

## Input Methods

The Claude CLI accepts prompts via two methods:

1. **Command-line argument** (limited):

   ```bash
   claude --print "Your prompt here"
   ```

   - Subject to OS argument list size limit (~128KB on Linux/macOS)
   - Will fail with `OSError: [Errno 7] Argument list too long` for large prompts

2. **Stdin** (preferred for programmatic use):

   ```bash
   echo "Your prompt here" | claude --print
   ```

   - No size limit (stdin is not subject to kernel arg limits)
   - Preferred for subprocess invocation with variable-size prompts

## Subprocess Invocation Pattern

When invoking Claude CLI from Python, pass the prompt via `input=` parameter:

```python
import subprocess

cmd = [
    "claude",
    "--print",
    "--model", model,
    "--dangerously-skip-permissions",
]

result = subprocess.run(
    cmd,
    input=prompt,  # Pass via stdin, not as argument
    capture_output=True,
    text=True,
    cwd=cwd,
    check=False,
)
```

## Key Flags

| Flag                             | Purpose                                           |
| -------------------------------- | ------------------------------------------------- |
| `--print`                        | Non-interactive mode, print response and exit     |
| `--model <name>`                 | Model selection (e.g., "haiku", "sonnet", "opus") |
| `--dangerously-skip-permissions` | Bypass permission prompts (for automation)        |
| `--output-format json`           | Structured JSON output                            |

## Reference

See `packages/erk-shared/src/erk_shared/prompt_executor/real.py` for the production implementation.
