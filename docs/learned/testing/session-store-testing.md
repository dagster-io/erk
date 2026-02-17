---
title: Testing with FakeClaudeInstallation
read_when:
  - "testing code that reads session data"
  - "using FakeClaudeInstallation"
  - "mocking session ID lookup"
last_audited: "2026-02-17 00:00 PT"
audit_result: edited
---

# Testing with FakeClaudeInstallation

`FakeClaudeInstallation` provides an in-memory fake for testing code that needs session store operations.

## When to Use

Use `FakeClaudeInstallation` when testing code that needs:

- Session discovery/listing
- Session content reading
- Project existence checks

## Reference Example

For a complete, up-to-date example of using `FakeClaudeInstallation`:

**See:** `tests/commands/cc/test_session_list.py`

This test file demonstrates:

- Creating `FakeClaudeInstallation` with `projects` parameter
- Using `FakeProject` and `FakeSessionData` to set up test sessions
- Injecting the fake via context builders
- Testing session listing with various scenarios (agents, limits, empty projects)

## Key Types

| Type                     | Purpose                                      |
| ------------------------ | -------------------------------------------- |
| `FakeClaudeInstallation` | In-memory fake implementing the ABC          |
| `FakeProject`            | Container for sessions in a project          |
| `FakeSessionData`        | Individual session with content and metadata |

## Related Topics

- [Session Layout](../sessions/layout.md) - JSONL format and directory structure
