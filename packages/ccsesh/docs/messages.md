# Message Types & Schemas

This document details the structure of messages in Claude Code session files.

## Message Types Overview

| Type        | Description        | Contains                    |
| ----------- | ------------------ | --------------------------- |
| `summary`   | Session metadata   | Summary text, leaf UUID     |
| `snapshot`  | Message checkpoint | Message ID, timestamp       |
| `user`      | User input         | Prompt text or tool results |
| `assistant` | Assistant response | Text, tool calls            |

## User Message Schema

```json
{
  "type": "user",
  "sessionId": "uuid",
  "uuid": "unique-message-id",
  "parentUuid": "parent-message-id",
  "message": {
    "role": "user",
    "content": [ ...content blocks... ]
  },
  "timestamp": "2024-01-15T10:30:00.000Z",
  "cwd": "/path/to/working/directory",
  "toolUseResult": { ... }  // Optional, for tool results
}
```

### User Message Fields

| Field             | Type    | Description                                |
| ----------------- | ------- | ------------------------------------------ |
| `type`            | string  | Always `"user"`                            |
| `sessionId`       | string  | Session identifier                         |
| `uuid`            | string  | Unique message ID                          |
| `parentUuid`      | string? | Parent message ID (null for first message) |
| `message.role`    | string  | Always `"user"`                            |
| `message.content` | array   | Content blocks                             |
| `timestamp`       | string  | ISO 8601 timestamp                         |
| `cwd`             | string  | Working directory at message time          |
| `toolUseResult`   | object? | Present when this is a tool result         |

## Assistant Message Schema

```json
{
  "type": "assistant",
  "sessionId": "uuid",
  "uuid": "unique-message-id",
  "parentUuid": "parent-message-id",
  "message": {
    "role": "assistant",
    "content": [ ...content blocks... ]
  },
  "costUSD": 0.0123,
  "durationMs": 1500,
  "model": "claude-sonnet-4-20250514"
}
```

### Assistant Message Fields

| Field             | Type   | Description                |
| ----------------- | ------ | -------------------------- |
| `type`            | string | Always `"assistant"`       |
| `sessionId`       | string | Session identifier         |
| `uuid`            | string | Unique message ID          |
| `parentUuid`      | string | Parent message ID          |
| `message.role`    | string | Always `"assistant"`       |
| `message.content` | array  | Content blocks             |
| `costUSD`         | number | API cost for this response |
| `durationMs`      | number | Response generation time   |
| `model`           | string | Model used for response    |

## Content Block Types

Messages contain arrays of content blocks. Each block has a `type` field.

### Text Block

Plain text content:

```json
{
  "type": "text",
  "text": "Here is the file contents..."
}
```

### Tool Use Block

Assistant requesting a tool call:

```json
{
  "type": "tool_use",
  "id": "toolu_01ABC123",
  "name": "Read",
  "input": {
    "file_path": "/path/to/file.py"
  }
}
```

| Field   | Description                         |
| ------- | ----------------------------------- |
| `id`    | Unique tool use identifier          |
| `name`  | Tool name (Read, Write, Bash, etc.) |
| `input` | Tool parameters                     |

### Tool Result Block

Result of a tool execution (in user messages):

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_01ABC123",
  "content": "File contents here..."
}
```

| Field         | Description                             |
| ------------- | --------------------------------------- |
| `tool_use_id` | References the `id` from tool_use block |
| `content`     | Tool output (string or array)           |

## Common Tools

| Tool Name   | Description                   |
| ----------- | ----------------------------- |
| `Read`      | Read file contents            |
| `Write`     | Write/create file             |
| `Edit`      | Edit file with search/replace |
| `Bash`      | Execute shell command         |
| `Glob`      | Find files by pattern         |
| `Grep`      | Search file contents          |
| `Task`      | Spawn sub-agent               |
| `TodoWrite` | Update task list              |
| `WebFetch`  | Fetch URL content             |
| `WebSearch` | Search the web                |

## Tool Result Reference

Large tool outputs may be stored externally:

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_01ABC123",
  "content": "[stored in .claude/projects/.../tool-results/toolu_01ABC123.txt]"
}
```

The actual content is in the referenced file.

## Example: Complete Exchange

```json
{"type":"summary","summary":"Debug login issue","leafUuid":"msg-003","version":"1"}
{"type":"user","uuid":"msg-001","parentUuid":null,"message":{"role":"user","content":[{"type":"text","text":"Why is login failing?"}]}}
{"type":"assistant","uuid":"msg-002","parentUuid":"msg-001","message":{"role":"assistant","content":[{"type":"text","text":"Let me check the auth code."},{"type":"tool_use","id":"toolu_01X","name":"Read","input":{"file_path":"/src/auth.py"}}]}}
{"type":"user","uuid":"msg-003","parentUuid":"msg-002","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"toolu_01X","content":"def login(user, pwd):\n  ..."}]}}
```

## Plan Mode Fields

When Plan Mode is used in a session, messages include a `slug` field:

```json
{
  "type": "assistant",
  "slug": "dazzling-herding-fox",
  "uuid": "...",
  ...
}
```

| Field  | Description                                                                 |
| ------ | --------------------------------------------------------------------------- |
| `slug` | Human-readable identifier for the plan, maps to `~/.claude/plans/{slug}.md` |

The slug appears on all messages in a session once Plan Mode has been used. Sessions without Plan Mode usage do not have this field.

Introduced in Claude Code v2.0.28 (October 27, 2025) with the new Plan subagent.
