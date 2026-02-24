# Plan: Eliminate sleep() calls from erkbot integration tests

## Context

The erkbot test suite takes 10.35s for 33 tests. **9.5s is pure `asyncio.sleep()`** in 10 integration tests. This is because Bolt's `async_dispatch()` returns before handlers finish (via `asyncio.ensure_future()`), and one-shot handlers spawn a second background task via `asyncio.create_task()`. Tests sleep to let these complete before asserting.

The fix is a `dispatch_and_settle` utility that tracks and awaits all background tasks spawned during dispatch, replacing arbitrary sleeps with deterministic completion.

## Implementation

### 1. Add `dispatch_and_settle` to conftest.py

**File**: `packages/erkbot/tests/integration/conftest.py`

Add imports: `asyncio`, `BoltResponse` (from `slack_bolt.response`).

Add standalone async function (not a fixture):

```python
async def dispatch_and_settle(
    app: AsyncApp,
    request: AsyncBoltRequest,
    *,
    timeout_seconds: float,
) -> BoltResponse:
    """Dispatch a Bolt request and wait for all spawned tasks to complete."""
    before = asyncio.all_tasks()
    response = await app.async_dispatch(request)

    deadline = asyncio.get_event_loop().time() + timeout_seconds
    while True:
        await asyncio.sleep(0)  # yield to let tasks get scheduled
        new_pending = [t for t in (asyncio.all_tasks() - before) if not t.done()]
        if not new_pending:
            break
        if asyncio.get_event_loop().time() > deadline:
            task_names = [t.get_name() for t in new_pending]
            raise TimeoutError(
                f"Tasks did not settle within {timeout_seconds}s: {task_names}"
            )
        await asyncio.gather(*new_pending, return_exceptions=True)

    return response
```

**How it works**:
- Snapshots tasks before dispatch
- After dispatch, finds new tasks (the handler Future from `ensure_future`)
- Awaits them; if the handler spawned more tasks (e.g. `create_task(run_one_shot_background(...))`), the loop catches and awaits those too
- `return_exceptions=True` prevents unexpected exceptions from masking the real test failure
- Safety timeout prevents infinite hangs

### 2. Update test_app_mention_integration.py

**File**: `packages/erkbot/tests/integration/test_app_mention_integration.py`

- Remove `import asyncio`
- Add `from tests.integration.conftest import dispatch_and_settle`
- Remove `HANDLER_SETTLE_SECONDS = 0.5` constant and its comment
- Replace all 9 occurrences of the pattern:
  ```python
  response = await app.async_dispatch(request)
  await asyncio.sleep(HANDLER_SETTLE_SECONDS)  # or 2.0
  ```
  with:
  ```python
  response = await dispatch_and_settle(app, request, timeout_seconds=5.0)
  ```

### 3. Update test_ping_integration.py

**File**: `packages/erkbot/tests/integration/test_ping_integration.py`

- Remove `import asyncio`
- Add `from tests.integration.conftest import dispatch_and_settle`
- Remove `HANDLER_SETTLE_SECONDS = 0.5` constant
- Replace the sleep pattern with `dispatch_and_settle` call

### 4. Update bolt-async-dispatch-testing.md

**File**: `docs/learned/testing/bolt-async-dispatch-testing.md`

Update the "Background Task Testing" section (lines 119-129) to document the `dispatch_and_settle` pattern instead of `asyncio.sleep()`.

## Files Modified

- `packages/erkbot/tests/integration/conftest.py` — add `dispatch_and_settle`
- `packages/erkbot/tests/integration/test_app_mention_integration.py` — replace 9 sleeps
- `packages/erkbot/tests/integration/test_ping_integration.py` — replace 1 sleep
- `docs/learned/testing/bolt-async-dispatch-testing.md` — update docs

## Verification

1. Run `make test-erkbot` — all 33 tests pass, runtime drops from ~10s to ~1s
2. Run integration tests in isolation: `cd packages/erkbot && uv run pytest tests/integration/ -x -q`
