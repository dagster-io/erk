---
title: Testing with FakeClaudeCodeSessionStore
read_when:
  - "testing code that reads session data"
  - "using FakeClaudeCodeSessionStore"
  - "mocking session ID lookup"
---

# Testing with FakeClaudeCodeSessionStore

`FakeClaudeCodeSessionStore` provides an in-memory fake for testing code that needs session store operations.

## When to Use

Use `FakeClaudeCodeSessionStore` when testing code that needs:

- Session discovery/listing
- Session content reading
- Project existence checks

## Reference Example

For a complete, up-to-date example of using `FakeClaudeCodeSessionStore`:

**See:** `tests/commands/cc/test_session_list.py`

This test file demonstrates:

- Creating `FakeClaudeCodeSessionStore` with `projects` parameter
- Using `FakeProject` and `FakeSessionData` to set up test sessions
- Injecting the fake via context builders
- Testing session listing with various scenarios (agents, limits, empty projects)

## Key Types

| Type                         | Purpose                                      |
| ---------------------------- | -------------------------------------------- |
| `FakeClaudeCodeSessionStore` | In-memory fake implementing the ABC          |
| `FakeProject`                | Container for sessions in a project          |
| `FakeSessionData`            | Individual session with content and metadata |

## Related Topics

- [Session Layout](.erk/docs/agent/sessions/layout.md) - JSONL format and directory structure
- [Kit CLI Testing Patterns](kit-cli-testing.md) - General patterns for testing kit CLI commands
