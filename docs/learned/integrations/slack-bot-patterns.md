---
title: Slack Bot Patterns
read_when:
  - "working with packages/erkbot/"
  - "adding new Slack bot commands"
  - "understanding streaming subprocess execution"
tripwires:
  - action: "using shell=True in subprocess calls for the Slack bot"
    warning: "Never use shell=True for security. Pass arguments as a list to prevent shell injection. See runner.py for the pattern."
---

# Slack Bot Patterns

The `erkbot` package (`packages/erkbot/`) integrates erk with Slack via Socket Mode. It handles command parsing, subprocess execution, and live progress streaming.

## Package Structure

```
packages/erkbot/src/erkbot/
├── app.py              # Slack app factory
├── cli.py              # CLI entry point
├── config.py           # Pydantic settings from environment
├── models.py           # Command discriminated unions
├── parser.py           # Text parsing (command extraction)
├── runner.py           # Subprocess execution and streaming
├── slack_handlers.py   # Handler registration and event logic
└── utils.py            # Formatting/streaming utilities
```

## Command Model

Commands are modeled as a discriminated union using Pydantic `BaseModel`:

- `PlanListCommand` - Lists plans
- `QuoteCommand` - Returns a random quote
- `OneShotCommand(message: str)` - Executes an erk one-shot with the message
- `OneShotMissingMessageCommand` - Error state when one-shot lacks content
- `ChatCommand(message: str)` - Agent-mode chat command

## Streaming Subprocess Execution

`runner.py` provides three execution modes:

1. **In-process** (`run_erk_plan_list`): Uses Click's `CliRunner` for fast execution
2. **Batch subprocess** (`run_erk_one_shot`): Runs subprocess, collects full output, handles timeout
3. **Streaming** (`stream_erk_one_shot`): Streams output line-by-line with progress callbacks

The streaming mode enables live Slack message updates during long-running operations. It uses `asyncio.create_subprocess_exec` with async line-by-line reading and a callback function for progress updates.

## LBYL Boundaries

The bot applies LBYL (Look Before You Leap) for Python-internal checks:

- Command parsing validates input before execution
- Config validation checks environment variables at startup

External Slack API calls use try/except since network operations are inherently unpredictable.

## Message Update Fallback

`slack_handlers.py` handles Slack API limitations:

- Primary: Update existing message with progress
- Fallback: Post new message if update fails (e.g., message too old)

## Security

Arguments are passed to subprocess as lists, never through shell interpolation:

```python
# Correct: async subprocess with list arguments
await asyncio.create_subprocess_exec("uv", "run", "erk", "one-shot", message)

# Never: shell=True with string
```

## Configuration

Via Pydantic settings from environment variables:

| Setting                        | Default  | Purpose                          |
| ------------------------------ | -------- | -------------------------------- |
| `SLACK_BOT_TOKEN`              | Required | Bot authentication               |
| `SLACK_APP_TOKEN`              | Required | Socket Mode connection           |
| `max_slack_code_block_chars`   | 2800     | Truncation limit for code blocks |
| `max_one_shot_message_chars`   | 1200     | Max message length               |
| `one_shot_timeout_seconds`     | 900      | One-shot execution timeout       |
| `one_shot_progress_tail_lines` | 40       | Lines shown in progress updates  |

## Related Topics

- [Multi-Agent Portability](multi-agent-portability.md) - Backend support patterns
