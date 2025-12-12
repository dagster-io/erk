## Objective

Create documentation for Claude CLI integration patterns used in erk, capturing input methods and subprocess invocation best practices.

## Source Information

- Session ID: 16d0a8f3-535d-45d2-a348-ce54498be45d
- Context: Bug fix for OSError when passing large prompts to Claude CLI

## Documentation Items

### Item 1: Claude CLI Integration Patterns

**Type:** Category B (Teaching Gap) - Document what was built/discovered
**Location:** docs/agent/architecture/claude-cli-patterns.md (new file)
**Action:** Create
**Priority:** Medium

**Content:**

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

| Flag | Purpose |
|------|---------|
| `--print` | Non-interactive mode, print response and exit |
| `--model <name>` | Model selection (e.g., "haiku", "sonnet", "opus") |
| `--dangerously-skip-permissions` | Bypass permission prompts (for automation) |
| `--output-format json` | Structured JSON output |

## Reference

See `packages/erk-shared/src/erk_shared/prompt_executor/real.py` for the production implementation.