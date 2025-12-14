# Claude Code Session Format

This documentation describes the data format used by Claude Code to store projects and sessions locally.

## What is ccsesh?

`ccsesh` is a Python package for inspecting Claude Code session data. It parses the local storage format used by Claude Code and provides programmatic access to:

- Projects and their sessions
- Message history and threading
- Tool usage and results

## Documentation

- [Projects](projects.md) - Directory structure and project organization
- [Sessions](sessions.md) - JSONL file format and message ordering
- [Messages](messages.md) - Message types, schemas, and content blocks

## Terminology

| Term              | Definition                                                                                        |
| ----------------- | ------------------------------------------------------------------------------------------------- |
| **Project**       | A directory on disk that Claude Code has been used in. Maps to a folder in `~/.claude/projects/`. |
| **Session**       | A single conversation with Claude Code. Stored as a `.jsonl` file.                                |
| **Message**       | A single turn in a conversation (user prompt or assistant response).                              |
| **Content Block** | A piece of content within a message (text, tool_use, tool_result).                                |
| **Tool Use**      | A tool call made by the assistant (e.g., Read, Write, Bash).                                      |
| **Tool Result**   | The output returned from a tool execution.                                                        |

## Storage Location

Claude Code stores all session data under:

```
~/.claude/projects/
```

Project folders use path encoding (slashes replaced with hyphens) to create unique folder names.
