# Integration Tests for erk-slack-bot via Bolt Dispatch

## Context

The erk-slack-bot has solid unit tests but they bypass Bolt's event dispatch pipeline — handlers are called directly with `AsyncMock` objects for `say`/`client`. This leaves gaps:

1. **`run_one_shot_background`** (the 50-line streaming orchestration flow) is completely untested
2. **Slack API error paths** (reaction failures, chat_update fallback to threaded replies) are untested
3. **Multi-call sequencing** (post → extract ts → update → fallback) isn't exercised

We'll adopt the same pattern used by the bolt-python SDK's own tests (`/Users/schrockn/code/githubs/bolt-python/tests/`): a mock HTTP server simulating the Slack Web API, a real `AsyncApp`, and `AsyncBoltRequest` objects dispatched through `app.async_dispatch()`. No Slack connection needed.

## Approach

### Mock Slack API Server

Adapted from bolt-python's `tests/mock_web_api_server/`, with three enhancements:

- **Auto-assign port** (`port=0`) instead of bolt-python's hardcoded 8888 — avoids conflicts
- **Endpoint-specific responses** — `chat.postMessage` returns `{"ok": true, "ts": "..."}` so `extract_slack_message_ts()` works naturally
- **Request body recording** — stores bodies per endpoint path for content-level assertions (bolt-python only tracks path counts)

### Bolt Dispatch Integration

Each test:
1. Creates a real `AsyncApp(client=web_client, signing_secret=signing_secret)`
2. Calls `register_handlers(app, settings=settings)` to wire up erk-slack-bot handlers
3. Builds a signed `AsyncBoltRequest` with a Slack event payload
4. Dispatches via `await app.async_dispatch(request)`
5. Asserts on mock server's recorded API calls (paths, counts, and request bodies)

### Runner Injection

Runner functions (`run_erk_plan_list`, `stream_erk_one_shot`) are patched since we're testing the Bolt dispatch → Slack API interaction, not subprocess execution. The runner layer has its own unit tests in `test_runner.py`.

### Background Task Capture

For one-shot tests that use `asyncio.create_task`, we capture the task and await it after dispatch:

```python
created_tasks = []
def capturing_create_task(coro, **kwargs):
    task = original_create_task(coro, **kwargs)
    created_tasks.append(task)
    return task
```

## Files to Create

### `tests/mock_web_api_server/__init__.py`
Setup/teardown helpers. Pattern from bolt-python `tests/mock_web_api_server/__init__.py`.

### `tests/mock_web_api_server/mock_handler.py`
HTTP handler returning endpoint-specific responses:
- `/auth.test` → `{"ok": true, "bot_id": "B123", "user_id": "U123", ...}`
- `/chat.postMessage` → `{"ok": true, "ts": "<counter>", "channel": "..."}`
- `/chat.update` → `{"ok": true}` (configurable to return errors)
- `/reactions.add` → `{"ok": true}` (configurable to return errors)
- Everything else → `{"ok": true}`

Records `(path, parsed_body)` to an `asyncio.Queue` for assertions.

Pattern from bolt-python `tests/mock_web_api_server/mock_handler.py`.

### `tests/mock_web_api_server/mock_server_thread.py`
Background thread running `HTTPServer` on auto-assigned port.
Pattern from bolt-python `tests/mock_web_api_server/mock_server_thread.py`.

### `tests/mock_web_api_server/received_requests.py`
Drains queue into dicts for assertions. Extends bolt-python's version with body tracking:
- `get_count(path)` → int
- `get_bodies(path)` → list of parsed request body dicts

Pattern from bolt-python `tests/mock_web_api_server/received_requests.py`.

### `tests/integration/__init__.py`
Empty.

### `tests/integration/conftest.py`
Shared fixtures:
- `mock_server` — starts/stops mock API server, yields server URL
- `web_client` — `AsyncWebClient(token="xoxb-valid", base_url=server_url)`
- `settings` — `Settings(SLACK_BOT_TOKEN="xoxb-valid", SLACK_APP_TOKEN="xapp-test")`
- `signing_secret` / `signature_verifier` — for request signing
- `build_app_mention_request(text)` — helper that builds a signed `AsyncBoltRequest` with an `app_mention` event containing the given text
- `build_message_request(text)` — helper for message events (ping)

### `tests/integration/test_app_mention_integration.py`
Tests dispatched through `app.async_dispatch()`:

| Test | Command | Asserts |
|------|---------|---------|
| `test_plan_list_success` | `<@B123> plan list` | reactions.add called, "Running..." posted, plan output in code blocks |
| `test_plan_list_error` | `<@B123> plan list` (runner fails) | error status line posted |
| `test_quote` | `<@B123> quote` | quote text posted |
| `test_one_shot_missing_message` | `<@B123> one-shot` | usage message posted |
| `test_one_shot_too_long` | `<@B123> one-shot <1500 chars>` | rejection message posted |
| `test_unknown_command` | `<@B123> hello` | help text with supported commands posted |
| `test_one_shot_success` | `<@B123> one-shot fix readme` | status message posted → progress updates via chat_update → PR/run URLs posted |
| `test_one_shot_failure` | `<@B123> one-shot fix readme` (runner fails) | failure message with exit code posted, tail output in code blocks |
| `test_one_shot_update_fallback` | `<@B123> one-shot fix readme` (chat_update errors) | fallback notice posted, output streamed as threaded replies |

### `tests/integration/test_ping_integration.py`

| Test | Trigger | Asserts |
|------|---------|---------|
| `test_ping` | message "ping" | reactions.add called, "Pong!" posted |

## Files to Modify

### `pyproject.toml`
Add `pytest` and `pytest-asyncio` to dev dependencies:
```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=1.0",
    "ruff>=0.15.0",
    "ty>=0.0.1a19",
]
```

### `Makefile`
Add test targets:
```makefile
test:
	uv run pytest tests/ -x -q

test-integration:
	uv run pytest tests/integration/ -x -q
```

## Key Reference Files

- **bolt-python mock server**: `/Users/schrockn/code/githubs/bolt-python/tests/mock_web_api_server/` (pattern source)
- **bolt-python event tests**: `/Users/schrockn/code/githubs/bolt-python/tests/scenario_tests_async/test_events.py` (dispatch pattern)
- **Handler under test**: `src/erk_slack_bot/slack_handlers.py` (register_handlers, handle_app_mention, handle_ping)
- **TS extraction**: `src/erk_slack_bot/utils.py:14` (extract_slack_message_ts — needs `{"ts": "..."}` in mock chat_postMessage response)
- **Runner functions**: `src/erk_slack_bot/runner.py` (patched in integration tests)
- **Existing unit tests**: `tests/test_slack_handlers.py` (current FakeApp approach, kept as-is)

## Verification

1. `uv run pytest tests/ -x -q` — all existing unit tests + new integration tests pass
2. `uv run pytest tests/integration/ -x -q` — integration tests pass in isolation
3. `uv run ruff check .` — no lint errors
4. `uv run ty check .` — no type errors
5. No Slack connection or tokens needed — mock server handles everything
