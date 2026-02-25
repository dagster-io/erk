# Fix erkbot test RuntimeWarnings

## Context

The `make all-ci` run fails because erkbot tests produce 3 `RuntimeWarning: coroutine was never awaited` warnings. These are garbage-collection-timing issues where coroutines created by mocks are never consumed.

## Fixes

### 1. `test_runner.py:test_stream_one_shot_timeout` (line 118)

**Problem:** `process = AsyncMock()` makes `process.terminate()` and `process.kill()` return coroutines. But on real `asyncio.Process`, these are synchronous methods. The coroutines are never awaited in `runner.py:88`.

**Fix:** After creating the `AsyncMock`, override `terminate` and `kill` with `MagicMock()`:
```python
process = AsyncMock()
process.terminate = MagicMock()
process.kill = MagicMock()
```

### 2. `test_slack_handlers.py:test_one_shot_starts_background_task` (line 64)

**Problem:** The mock `asyncio.create_task` captures the `run_one_shot_background(...)` coroutine but never closes it. The coroutine is garbage collected later (during `test_ping`), triggering the warning.

**Fix:** Close the captured coroutine after the assertion:
```python
mock_asyncio.create_task.assert_called_once()
mock_asyncio.create_task.call_args[0][0].close()
```

### 3. `test_slack_handlers.py:test_chat_with_bot_starts_background_task` (line 96)

**Problem:** Same pattern as #2 — `asyncio.create_task` captures `run_agent_background(...)` coroutine without closing it.

**Fix:** Same approach:
```python
mock_asyncio.create_task.assert_called_once()
mock_asyncio.create_task.call_args[0][0].close()
```

## Files to modify

- `packages/erkbot/tests/test_runner.py` — add `MagicMock()` overrides for `terminate`/`kill`
- `packages/erkbot/tests/test_slack_handlers.py` — close captured coroutines in two tests

## Verification

Run: `make all-ci` (or just erkbot tests: `cd packages/erkbot && pytest`)
- All 114 erkbot tests pass
- 0 warnings
