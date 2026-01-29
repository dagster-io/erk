---
title: PreToolUse Hook Implementation Guide
read_when:
  - "creating a PreToolUse hook"
  - "reading tool_input from stdin JSON"
  - "detecting file types in hooks"
tripwires:
  - action: "creating a PreToolUse hook"
    warning: "Test against edge cases. Untested hooks fail silently (exit 0, no output). Read docs/learned/testing/hook-testing.md first."
---

# PreToolUse Hook Implementation Guide

PreToolUse hooks fire before a tool executes and can inject reminders or block execution. This guide covers the implementation patterns used in erk.

## Stdin JSON Protocol

PreToolUse hooks receive JSON on stdin with this structure:

```json
{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "content": "..."
  }
}
```

The `tool_input` fields vary by tool. Common fields:

- `Write`/`Edit`: `file_path` (the target file)
- `Bash`: `command` (the shell command)
- `Task`: `prompt`, `subagent_type`

## File Path Extraction

Extract `tool_input.file_path` with LBYL checks at each level:

1. Parse JSON from stdin
2. Check `tool_input` exists and is a dict
3. Check `file_path` exists and is a non-empty string

**Edge cases to handle**:

- Empty stdin (no JSON)
- Missing `tool_input` key
- `tool_input` is not a dict (e.g., string or null)
- `file_path` is empty string or non-string type
- Relative paths, paths with spaces

See `src/erk/cli/commands/exec/scripts/pre_tool_use_hook.py` for the canonical implementation using pure functions.

## File Type Detection

For detecting Python files:

- Check `file_path.endswith(".py")`
- `.pyi` stub files are NOT matched (by design — stubs rarely need coding standard reminders)
- Files with no extension are not matched

## Exit Code Behavior

| Exit Code | Effect                                                   |
| --------- | -------------------------------------------------------- |
| 0         | Proceed with tool execution; stdout is a system reminder |
| 2         | Block tool execution; stdout shown as error              |
| Other     | Non-blocking error, logged but tool proceeds             |

For informational hooks (reminders), always exit 0. The hook should never block the tool unless the action is genuinely unsafe.

## Settings.json Matcher Configuration

PreToolUse hooks use matchers to target specific tools:

```json
{
  "PreToolUse": [
    {
      "matcher": "Write|Edit",
      "hooks": [{ "type": "command", "command": "..." }]
    }
  ]
}
```

The matcher value is a **regex pattern**:

| Pattern       | Matches              |
| ------------- | -------------------- |
| `Write`       | Only Write tool      |
| `Edit`        | Only Edit tool       |
| `Write\|Edit` | Write OR Edit tools  |
| `Bash`        | Only Bash tool       |
| `.*`          | All tools (wildcard) |

The `|` character is regex OR. To match a literal pipe, escape with `\\|`.

## Implementation Architecture

The erk PreToolUse hook uses a three-layer architecture:

1. **Pure functions**: `extract_file_path_from_stdin()`, `is_python_file()`, `build_pretool_dignified_python_reminder()` — all independently testable
2. **Capability check**: `is_reminder_installed()` verifies the dignified-python capability is active
3. **Hook entry point**: Orchestrates the pure functions and capability check

This separation enables comprehensive unit testing without needing Claude Code infrastructure.

## Reference

- Implementation: `src/erk/cli/commands/exec/scripts/pre_tool_use_hook.py`
- Tests: `tests/unit/cli/commands/exec/scripts/test_pre_tool_use_hook.py`
- Settings: `.claude/settings.json` (PreToolUse section)
- Hook decorator: `src/erk/hooks/decorators.py`

## Related Topics

- [Three-Tier Context Injection](../architecture/context-injection-tiers.md) — Where PreToolUse fits in the injection architecture
- [Hooks Guide](hooks.md) — General hook lifecycle and configuration
- [Hook Testing Patterns](../testing/hook-testing.md) — Testing patterns for hooks
