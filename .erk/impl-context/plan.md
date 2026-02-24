# Plan: Objective #8036, Node 1.3 — ErkBot Class with Streaming and Emoji Lifecycle

> Part of Objective #8036, Node 1.3

## Context

The erk-slack-bot is being migrated from subprocess-based command execution to agent-mode using `claude-agent-sdk`. Node 1.1 (async migration) and 1.2 (agent event loop) are complete. Node 1.3 creates the core `ErkBot` class that streams agent responses to Slack with eyes emoji lifecycle management.

The bot currently handles `@erk one-shot <msg>` via subprocess. This plan adds `@erk chat <msg>` as a parallel agent-mode path, keeping both active during migration.

## New Files

### 1. `src/erkbot/agent/bot.py` — ErkBot class

Frozen dataclass wrapping `claude_agent_sdk.query()`. Produces `AsyncIterator[AgentEvent]` via the existing `stream_agent_events()` converter.

```python
@dataclass(frozen=True)
class ErkBot:
    model: str
    max_turns: int
    cwd: Path
    system_prompt: str
    permission_mode: str  # SDK Literal type at boundary

    async def chat_stream(self, *, prompt: str) -> AsyncIterator[AgentEvent]:
        # Construct ClaudeAgentOptions, call query(), pipe through stream_agent_events()
```

- Uses `query()` (one-shot, not bidirectional `ClaudeSDKClient`)
- All params explicit, no defaults (dignified-python)
- `cwd` as `Path`, converted to `str` at SDK boundary

### 2. `src/erkbot/emoji.py` — Emoji lifecycle functions

Extract eyes emoji pattern from `slack_handlers.py` closure into standalone module:

- `add_eyes_emoji(client, *, channel, timestamp)` — add eyes reaction
- `remove_eyes_emoji(client, *, channel, timestamp)` — remove eyes (ignores `no_reaction`)
- `add_result_emoji(client, *, channel, timestamp, success)` — checkmark or X

Same error-handling pattern as existing `add_read_ack()`: catch `SlackApiError`, ignore known harmless errors, re-raise others.

### 3. `src/erkbot/agent_handler.py` — Slack streaming handler

Connects `ErkBot.chat_stream()` to Slack message lifecycle:

```python
async def run_agent_background(
    *,
    client: Any,
    channel: str,
    reply_thread_ts: str | None,
    source_ts: str,
    prompt: str,
    bot: ErkBot,
    progress_update_interval_seconds: float,
    max_slack_code_block_chars: int,
) -> None:
```

Flow:
1. Post initial "Thinking..." status message
2. Iterate `bot.chat_stream()`, accumulate text
3. Rate-limited `chat_update()` for progress (reuses `progress_update_interval_seconds`)
4. Post final response as chunked messages (reuse `chunk_for_slack` from `utils.py`)
5. In `finally` block: remove eyes emoji, add result emoji

Also: private `_build_progress_display(*, text, tool_active)` for formatting.

## Modified Files

### 4. `src/erkbot/models.py` — Add ChatCommand

```python
class ChatCommand(BaseModel):
    type: Literal["chat"] = "chat"
    message: str = Field(min_length=1)
```

Update `Command` union to include `ChatCommand`.

### 5. `src/erkbot/parser.py` — Parse `chat` command

Add after one-shot matching:
- `@erk chat <message>` → `ChatCommand(message=...)`
- `@erk chat` (no message) → return `None` (triggers default greeting)

### 6. `src/erkbot/slack_handlers.py` — Wire ChatCommand handler

- Change `register_handlers` signature: add `bot: ErkBot | None` parameter
- Add `ChatCommand` branch in `handle_app_mention`:
  - If `bot is None` → "Agent mode is not configured."
  - Otherwise → `asyncio.create_task(run_agent_background(...))`
- Existing `add_read_ack` closure remains unchanged (old path still works)

### 7. `src/erkbot/app.py` — Accept bot parameter

```python
def create_app(*, settings: Settings, bot: ErkBot | None) -> AsyncApp:
```

### 8. `src/erkbot/cli.py` — Pass bot=None

Pass `bot=None` to `create_app`. Node 1.5 will construct and pass a real ErkBot.

## Tests

### New test files

- **`tests/test_bot.py`** — Mock `query()` via `@patch("erkbot.agent.bot.query")`, verify `chat_stream` yields correct `AgentEvent` sequence, verify `ClaudeAgentOptions` constructed correctly
- **`tests/test_emoji.py`** — AsyncMock client, verify `reactions_add`/`reactions_remove` calls, verify ignored errors (already_reacted, no_reaction), verify re-raise on unexpected errors, verify result emoji (checkmark/X)
- **`tests/test_agent_handler.py`** — Mock ErkBot with fake `chat_stream`, verify full lifecycle: status posted → text posted → status updated → eyes removed → result emoji added. Also test error case (stream raises) and empty response case.

### Modified test files

- **`tests/test_parser.py`** — Add `test_parse_chat_command`, `test_parse_chat_no_message`
- **`tests/test_slack_handlers.py`** — Update `setUp` to pass `bot=None`, add test for ChatCommand dispatch
- **`tests/test_app.py`** — Update to pass `bot=None`
- **`tests/test_cli.py`** — Update to verify `create_app` called with `bot=None`

## Implementation Order

1. `models.py` + `parser.py` — Add ChatCommand, parser logic
2. `emoji.py` — New file, standalone
3. `agent/bot.py` — New file, depends on existing `agent/stream.py`
4. `agent_handler.py` — New file, depends on bot.py and emoji.py
5. `slack_handlers.py` → `app.py` → `cli.py` — Wire everything together
6. All tests

## Out of Scope

| Deferred to | What |
|---|---|
| Node 1.4 | Config fields: `ANTHROPIC_API_KEY`, `ERK_REPO_PATH`, `ERK_MODEL`, `max_turns` in Settings |
| Node 1.5 | CLI wiring: construct ErkBot from Settings, pass to create_app |
| Node 1.7 | System prompt content in prompts.py |
| Node 6.1 | Remove old subprocess modules, consolidate emoji handling |

## Verification

1. Run `make fast-ci` in `packages/erkbot/` — all existing + new tests pass
2. Run `make all-ci` — full lint/type/test suite passes
3. Manual smoke test: With `bot=None`, existing `@erk one-shot`, `@erk plan list`, `@erk quote` commands work unchanged
4. Manual smoke test: `@erk chat hello` returns "Agent mode is not configured." (expected until Node 1.5 wires config)
