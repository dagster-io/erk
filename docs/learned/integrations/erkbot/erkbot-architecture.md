---
title: ErkBot Architecture
read_when:
  - "working with erkbot Slack integration"
  - "modifying erkbot command handling or progress updates"
  - "understanding erkbot's design patterns"
tripwires:
  - action: "adding a Slack API call without error handling in agent_handler.py"
    warning: "ErkBot uses best-effort operations for Slack API calls. Wrap in try/except and log, don't raise. Agent execution should never fail due to a Slack API hiccup."
  - action: "adding a new erkbot command type without updating parser.py"
    warning: "New commands must be added to both parser.py (parse_erk_command) and slack_handlers.py (the app_mention handler's dispatch logic)."
  - action: "running uv sync without --package flag for workspace packages"
    warning: "For workspace packages like erkbot, use 'uv sync --package erkbot' instead of bare 'uv sync'. Bare sync resolves the root package, not the workspace member."
    score: 5
---

# ErkBot Architecture

ErkBot is a Slack bot that provides an interface to erk's planning and agent capabilities. It runs as an async Socket Mode application using `slack_bolt`.

## Core Design

<!-- Source: packages/erkbot/src/erkbot/agent/bot.py, ErkBot -->

`ErkBot` is a frozen dataclass with five fields: `model`, `max_turns`, `cwd`, `system_prompt`, `permission_mode`. Its single public method `chat_stream()` creates `ClaudeAgentOptions` and yields `AgentEvent` instances via the Claude Agent SDK's `query()` function.

## Emoji Lifecycle Management

<!-- Source: packages/erkbot/src/erkbot/emoji.py -->

Three functions in `emoji.py` manage Slack reaction emoji as processing indicators:

- **`add_eyes_emoji()`** — Added when a message is first received (indicates "processing")
- **`remove_eyes_emoji()`** — Removed when processing completes
- **`add_result_emoji()`** — Adds checkmark (success) or X (failure) based on outcome

All emoji operations define a local `ignored_errors` set internally for graceful handling of race conditions (e.g., removing an already-removed emoji). Each function catches `SlackApiError` and re-raises only if the error code is not in its ignored set.

## Rate-Limited Progress Updates

<!-- Source: packages/erkbot/src/erkbot/agent_handler.py, run_agent_background -->

`run_agent_background()` in `agent_handler.py` streams agent events and posts periodic progress updates to Slack threads. Progress updates are rate-limited using a monotonic clock interval (configurable via `one_shot_progress_update_interval_seconds` in config, default 1.0) to avoid Slack API rate limits.

The progress display shows the last 2000 characters of accumulated text.

## Best-Effort Operations Pattern

Slack API calls in `agent_handler.py` use a best-effort pattern: failures are caught, logged, and silently ignored. The agent's work is the priority; Slack notification failures should never interrupt it. This applies to progress updates, emoji reactions, and final message posting.

## Command Dispatch

<!-- Source: packages/erkbot/src/erkbot/parser.py, parse_erk_command -->

`parse_erk_command()` parses Slack messages into typed command models:

- `"plan list"` -> `PlanListCommand`
- `"quote"` -> `QuoteCommand`
- `"chat <message>"` -> `ChatCommand`
- `"one-shot <message>"` -> `OneShotCommand`

<!-- Source: packages/erkbot/src/erkbot/slack_handlers.py, register_handlers -->

The `app_mention` event handler in `slack_handlers.py` dispatches each command type to its handler: `PlanListCommand` runs `erk pr list`, `OneShotCommand` streams `erk one-shot` in a background task, and `ChatCommand` runs the agent via `run_agent_background()`.

## Parameter Threading for Dependency Injection

ErkBot uses explicit parameter threading rather than global state for dependency injection. The `bot: ErkBot` instance and `time: Time` abstraction are passed through function parameters from the CLI entry point (`cli.py`) through app creation (`app.py`) to handlers (`slack_handlers.py`).

## Related Documentation

- [Agent Event System](agent-event-system.md) — Typed event streaming pipeline
- [Bolt Async Dispatch Testing](../../testing/bolt-async-dispatch-testing.md) — Testing Slack handlers without live connection
