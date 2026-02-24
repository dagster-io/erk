# Plan: Address PR #8087 Review Comments — Time Gateway + Divergence Comments

## Context

PR #8087 "Add ErkBot class with streaming agent support and emoji lifecycle" received 5 tripwire review comments flagging `import time` / `time.monotonic()` usage and `@patch` usage in tests. The user decided:
- **Items #1, #2** (agent_handler.py): Add `erk-shared` dependency and reuse the Time gateway
- **Items #3, #4, #5** (test files): Add divergence comments — but item #3 is naturally resolved by the Time gateway refactor

The Time ABC currently lacks `monotonic()`, which erkbot uses for progress update throttling. This plan extends the gateway and threads it through erkbot.

Also fixes: ruff I001 import sort error in `test_emoji.py`.

## Changes

### 1. Extend Time gateway with `monotonic()` (erk-shared)

**`packages/erk-shared/src/erk_shared/gateway/time/abc.py`** — Add abstract method:
```python
@abstractmethod
def monotonic(self) -> float: ...
```

**`packages/erk-shared/src/erk_shared/gateway/time/real.py`** — Implement:
```python
def monotonic(self) -> float:
    return time.monotonic()
```

**`packages/erk-shared/src/erk_shared/gateway/time/fake.py`** — Add `monotonic_values` constructor param:
- `FakeTime(monotonic_values=[100.0])` → always returns 100.0
- `FakeTime(monotonic_values=[2.0, 4.0, 6.0])` → returns sequence, clamps to last
- Default `[0.0]` when not specified
- Tracks call count via `_monotonic_index`

### 2. Add `erk-shared` dependency to erkbot

**`packages/erkbot/pyproject.toml`**:
- Add `"erk-shared"` to dependencies
- Add `erk-shared = { workspace = true }` to `[tool.uv.sources]`

### 3. Thread Time through erkbot production code

The call chain: `cli._run()` → `create_app()` → `register_handlers()` → `run_agent_background()`

**`packages/erkbot/src/erkbot/agent_handler.py`**:
- Remove `import time`, add `from erk_shared.gateway.time.abc import Time`
- Add `time: Time` parameter to `run_agent_background()`
- Existing `time.monotonic()` calls now invoke the gateway method (parameter shadows module)

**`packages/erkbot/src/erkbot/slack_handlers.py`**:
- Remove `import time`, add `from erk_shared.gateway.time.abc import Time`
- Add `time: Time` parameter to `register_handlers()`
- Inner `push_progress_update()` accesses `time` via closure
- Pass `time=time` to `run_agent_background()` call

**`packages/erkbot/src/erkbot/app.py`**:
- Add `time: Time` parameter to `create_app()`, pass through to `register_handlers()`

**`packages/erkbot/src/erkbot/cli.py`**:
- Create `RealTime()` in `_run()`, pass to `create_app()`

### 4. Update tests

**`packages/erkbot/tests/test_agent_handler.py`** — Replace all 4 `@patch("erkbot.agent_handler.time")` with FakeTime injection:
- Remove `patch` import, add `from erk_shared.gateway.time.fake import FakeTime`
- Each test creates `FakeTime(monotonic_values=[...])` and passes `time=fake_time`
- `test_full_lifecycle_success`: `monotonic_values=[100.0]`
- `test_error_in_stream`: `monotonic_values=[0.0]`
- `test_empty_response`: `monotonic_values=[100.0]`
- `test_tool_events_track_active_state`: `monotonic_values=[2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0]`

**`packages/erkbot/tests/test_bot.py`** — Add divergence comment (line 1):
```python
# NOTE: @patch usage is deliberate here. These tests verify the wiring between
# ErkBot and the claude-agent-sdk third-party library (query/stream_agent_events),
# which cannot be replaced with erk gateway fakes.
```

**`packages/erkbot/tests/test_slack_handlers.py`** — Add divergence comment (line 1) + update `register_handlers` calls:
```python
# NOTE: @patch usage is deliberate here. These tests patch asyncio.create_task
# and run_erk_plan_list to verify Slack handler dispatch without launching real
# background tasks or subprocess calls.
```
- `setUp`: pass `time=FakeTime()` to `register_handlers()`
- `test_chat_with_bot_starts_background_task`: pass `time=FakeTime()` to `register_handlers()`

**`packages/erkbot/tests/test_app.py`** — Update assertion to include `time=`:
- Pass `time=FakeTime()` to `create_app()`
- Update `mock_register.assert_called_once_with(...)` to include `time=fake_time`

**`packages/erkbot/tests/test_cli.py`** — Update assertion:
- Add `from unittest.mock import ANY`
- Update `mock_create_app.assert_called_once_with(...)` to include `time=ANY`

### 5. Fix lint

**`packages/erkbot/tests/test_emoji.py`** — Reorder imports: `erkbot` before `slack_sdk` (both third-party, alphabetical).

## Verification

1. `uv sync` to update lockfile with new dependency
2. `make all-ci` — all checks should pass (lint, format, ty, tests)
3. Specifically verify: `uv run pytest packages/erkbot/tests/ -v`
