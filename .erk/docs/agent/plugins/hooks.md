---
title: Plugin Hook Configuration
read_when:
  - configuring plugin hooks
  - writing hooks.json
  - understanding hook lifecycle events
---

# Plugin Hook Configuration

> **Note:** This documentation was produced in December 2025 based on Claude Code's plugin system at that time. The plugin system is actively evolving; verify against [official Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code) for current behavior.

Hooks execute at specific points in Claude Code's lifecycle.

## hooks.json Location

```
{plugin}/
└── hooks/
    └── hooks.json
```

## Hook Events

| Event               | When it fires                     |
| ------------------- | --------------------------------- |
| `SessionStart`      | When a session begins             |
| `UserPromptSubmit`  | When user submits input           |
| `PreToolUse`        | Before tool execution (can block) |
| `PostToolUse`       | After tool execution              |
| `PermissionRequest` | When permission is needed         |
| `Notification`      | When Claude sends notifications   |
| `Stop`              | End-of-turn quality gates         |

## hooks.json Schema

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*.py",
        "hooks": [
          {
            "type": "command",
            "command": "uvx erk@1.2.3 kit exec dignified-python version-aware-reminder",
            "timeout": 30
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "ExitPlanMode",
        "hooks": [
          {
            "type": "command",
            "command": "uvx erk@1.2.3 kit exec erk exit-plan-mode-hook",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

## Matcher Patterns

| Pattern        | Matches                 |
| -------------- | ----------------------- |
| `*`            | All events              |
| `*.py`         | Python files in context |
| `Bash`         | Bash tool use           |
| `Edit\|Write`  | Edit or Write tool use  |
| `ExitPlanMode` | ExitPlanMode tool use   |

## Hook Exit Codes

| Code  | Meaning                                   |
| ----- | ----------------------------------------- |
| `0`   | Success (stdout shown in transcript mode) |
| `2`   | Blocking error (stderr fed to Claude)     |
| Other | Non-blocking error (stderr shown to user) |

## JSON Output from Hooks

Hooks can return structured JSON:

```json
{
  "continue": true,
  "stopReason": "Optional message if continue is false",
  "suppressOutput": false,
  "systemMessage": "Optional warning shown to user"
}
```

## Environment Variables

| Variable              | Description                    |
| --------------------- | ------------------------------ |
| `$CLAUDE_PROJECT_DIR` | Project root absolute path     |
| `$CLAUDE_PLUGIN_ROOT` | Plugin installation directory  |
| `$CLAUDE_FILE_PATHS`  | Space-separated file paths     |
| `$CLAUDE_TOOL_OUTPUT` | Tool output (PostToolUse only) |

## ERK Hook Pattern

ERK hooks use uvx for reproducibility:

```json
{
  "type": "command",
  "command": "uvx erk@1.2.3 kit exec erk session-id-injector-hook",
  "timeout": 30
}
```

See [uvx Hook Pattern](../architecture/uvx-hooks.md) for the full rationale.
