---
title: Exec Script Error Handling
read_when:
  - "implementing error handling in exec scripts"
  - "wrapping file operations in exec commands"
  - "handling git errors in exec scripts"
---

# Exec Script Error Handling

## File Write Operations

When exec scripts write files, catch broad exceptions and wrap in specific error codes.

See source implementations for the pattern. The key principle:

- Wrap file operations in try/except blocks
- Return structured error dataclasses with specific error codes
- Include original exception message in the message field

### Why This Pattern

Without wrapping:

- Raw exception messages leak into JSON output
- Subprocess-style errors (exit codes, stderr) break JSON parsing
- Callers can't programmatically handle failures

With wrapping:

- JSON structure is always valid
- Error codes enable programmatic handling
- Messages remain human-readable

### Error Code Guidelines

- Use specific codes: `git_error`, `file_write_error`, `network_error`
- Avoid generic codes: `error`, `failed`, `unknown`
- Include original exception message in `message` field

## Related Topics

- [Exec Script Patterns](exec-script-patterns.md) - Template structure
- [erk exec Commands](erk-exec-commands.md) - Command reference
