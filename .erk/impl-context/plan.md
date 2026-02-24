# Documentation Plan: Complete async migration of erk-slack-bot with AsyncApp and asyncio subprocess

## Context

This PR performs a complete mechanical migration of the erk-slack-bot package from synchronous to fully asynchronous architecture. The migration replaces `slack_bolt.App` with `AsyncApp`, converts all event handlers to async functions, eliminates the Thread+Queue pattern for subprocess streaming in favor of native `asyncio.create_subprocess_exec`, and updates the entire test infrastructure to use `IsolatedAsyncioTestCase` with `AsyncMock`.

Future agents working with async code in erk will benefit significantly from this documentation. The patterns discovered are broadly applicable beyond erk-slack-bot: async subprocess execution is fundamental infrastructure (subprocess calls are pervasive in erk), and the Thread+Queue antipattern elimination prevents a common architectural mistake. The async testing patterns (IsolatedAsyncioTestCase, AsyncMock) enable correct testing of any future async code, preventing "tests pass but runtime fails" scenarios.

Key non-obvious learnings include: async libraries with constructors (aiohttp.ClientSession, AsyncSocketModeHandler) require instantiation inside a running event loop context; mocking asyncio.run() in tests can mask real instantiation errors by preventing actual async code execution; and the on_line callback signature change for streaming functions is a breaking change that propagates through entire callback chains.

## Raw Materials

PR #8039

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 13    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 5     |
| Potential tripwires (score2-3) | 3     |

## Documentation Items

### HIGH Priority

#### 1. Async subprocess execution patterns

**Location:** `docs/learned/architecture/async-subprocess-patterns.md`
**Action:** CREATE
**Source:** [PR #8039]

**Draft Content:**

```markdown
---
description: Patterns for asyncio.create_subprocess_exec, timeout handling, and graceful shutdown
read-when:
  - writing async code that runs subprocesses
  - migrating synchronous subprocess calls to async
  - implementing timeout handling for subprocess execution
tripwires: 2
---

# Async Subprocess Execution Patterns

When running subprocesses in async code, use `asyncio.create_subprocess_exec` instead of `subprocess.run` or `subprocess.Popen`.

## Core Pattern

See `packages/erk-slack-bot/src/erk_slack_bot/runner.py` for implementation examples.

Key points to cover:
- `asyncio.create_subprocess_exec` vs `subprocess.run`: async subprocess does not block the event loop
- Timeout handling with `asyncio.wait_for` wrapping `process.communicate()`
- Graceful shutdown cascade: `terminate()` -> 2-second wait -> `kill()` for hung processes
- Exit code 124 convention for timeouts (matches GNU timeout)
- Byte decoding: subprocess returns bytes, must decode to str
- `asyncio.to_thread` for sync-only APIs that cannot be rewritten (e.g., Click CliRunner)

## See Also

- [Async Subprocess Streaming](async-subprocess-streaming.md)
- [Async Entry Points](async-entry-points.md)
- [Testing patterns](../testing/async-test-patterns.md)
```

---

#### 2. Async subprocess streaming patterns (Thread+Queue elimination)

**Location:** `docs/learned/architecture/async-subprocess-streaming.md`
**Action:** CREATE
**Source:** [PR #8039]

**Draft Content:**

```markdown
---
description: Streaming subprocess output with async readline loops, replacing Thread+Queue antipattern
read-when:
  - streaming subprocess output in async code
  - tempted to use Thread + Queue for subprocess output
  - implementing progress callbacks for long-running processes
tripwires: 1
---

# Async Subprocess Streaming

Streaming subprocess output in async code uses direct `await process.stdout.readline()` loops.

## Antipattern: Thread + Queue

Never use Thread + Queue to stream subprocess output. This pattern introduces:
- Polling overhead (time.sleep delays)
- Thread synchronization complexity
- Queue memory overhead
- Blocking I/O in async context

## Correct Pattern

See `packages/erk-slack-bot/src/erk_slack_bot/runner.py`, grep for `stream_erk_one_shot` and `_read_lines`.

Key points to cover:
- Inner async function with `while True: await process.stdout.readline()` loop
- Timeout wrapping the entire readline coroutine with `asyncio.wait_for`
- Breaking change: `on_line` callback signature must return `Awaitable[None]`
- stderr merging with `stderr=asyncio.subprocess.STDOUT` for unified output stream
- Graceful shutdown on timeout

## See Also

- [Async Subprocess Patterns](async-subprocess-patterns.md)
```

---

#### 3. Architecture tripwires: async library instantiation and subprocess patterns

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8039]

**Draft Content:**

Add the following tripwires:

1. **BEFORE instantiating async libraries (aiohttp.ClientSession, aioboto3, AsyncSocketModeHandler)**: Ensure instantiation happens inside async function called by `asyncio.run()`, not in synchronous entry points. Use `async def _run()` + `asyncio.run(_run())` pattern.

2. **BEFORE using Thread + Queue to stream subprocess output**: Use `asyncio.create_subprocess_exec` with direct readline loop instead. Thread+Queue is an antipattern for async code.

3. **BEFORE calling subprocess.run() or subprocess.Popen() in async code**: Use `asyncio.create_subprocess_exec` to avoid blocking event loop. Synchronous subprocess calls block all async tasks.

4. **BEFORE using time.sleep() or polling loops in async code**: Use `asyncio.sleep()` and event-driven patterns (await readline(), wait_for(), etc.) instead.

Add **Known Acceptable Patterns** section:
- `import time` + `time.monotonic()` for rate-limiting: Legitimate use case for monotonic clock, not a testability concern
- Long-running synchronous operations: Use `asyncio.to_thread()` when rewriting with async primitives is not feasible (e.g., CliRunner)

---

#### 4. Testing tripwires: AsyncMock and async test patterns

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8039]

**Draft Content:**

Add the following tripwires:

1. **BEFORE mocking async functions or testing async code**: Use `AsyncMock` and `new_callable=AsyncMock` for patches. Use `IsolatedAsyncioTestCase` for test classes. Use `assert_awaited_once()` to verify awaiting.

2. **BEFORE mocking asyncio.run() or entire async runtime**: Mock specific async behaviors (methods, functions) instead. Mocking `asyncio.run` prevents real instantiation and can mask constructor errors.

3. **BEFORE patching asyncio.create_subprocess_exec**: Process mock must be `AsyncMock` with async `communicate()`, `wait()`, `terminate()`, `kill()` methods. `communicate()` returns `(bytes, bytes)` tuple.

4. **BEFORE testing async timeouts**: Use `AsyncMock(side_effect=async_hang_function)` where hang sleeps longer than timeout. Verify `process.terminate.assert_called_once()`.

Add **Known Acceptable Patterns** section:
- `@patch` for third-party SDK testing: Acceptable in standalone packages outside erk's gateway layer (e.g., erk-slack-bot testing Slack SDK wiring).

---

#### 5. Async test patterns guide

**Location:** `docs/learned/testing/async-test-patterns.md`
**Action:** CREATE
**Source:** [Impl], [PR #8039]

**Draft Content:**

```markdown
---
description: Comprehensive patterns for testing async code with IsolatedAsyncioTestCase and AsyncMock
read-when:
  - writing tests for async functions
  - testing async subprocess execution
  - testing async event handlers or callbacks
tripwires: 4
---

# Async Test Patterns

This guide covers testing patterns for async code using Python's unittest framework.

## IsolatedAsyncioTestCase

Use `unittest.IsolatedAsyncioTestCase` (Python 3.11+) as base class for async tests.

Key points:
- Test methods become `async def` and use `await` when calling async functions
- Each test gets an isolated event loop

## AsyncMock Patterns

See `packages/erk-slack-bot/tests/` for implementation examples.

### Basic AsyncMock Usage
- Use `AsyncMock` for mocking async functions and coroutines
- Use `new_callable=AsyncMock` when patching async functions

### Subprocess Mocking
- Mock `asyncio.create_subprocess_exec`, not `subprocess.run`/`Popen`
- Process mock must be `AsyncMock` with async `communicate()`, `wait()`
- Subprocess returns bytes: `communicate()` returns `(b"stdout", b"stderr")`

### Handler Testing
- `say` and `client` must be `AsyncMock` for async handlers
- Handler invocation requires `await handler(...)`
- Use `assert_awaited_once()` to verify async function was awaited (not just called)

### Timeout Testing
- Simulate timeouts with `AsyncMock(side_effect=async_hang_function)`
- Hang function must sleep longer than `timeout_seconds` parameter
- Verify `process.terminate.assert_called_once()` for graceful shutdown

### Background Task Testing
- Mock entire `asyncio` module to intercept `create_task` calls
- Verify `mock_asyncio.create_task.assert_called_once()`
- Task doesn't execute in test (no lifecycle verification needed)

## See Also

- [Async Subprocess Patterns](../architecture/async-subprocess-patterns.md)
```

---

### MEDIUM Priority

#### 6. Async background tasks

**Location:** `docs/learned/architecture/async-background-tasks.md`
**Action:** CREATE
**Source:** [PR #8039]

**Draft Content:**

```markdown
---
description: Using asyncio.create_task for fire-and-forget async operations
read-when:
  - implementing background work in async code
  - migrating Thread(daemon=True) to async patterns
tripwires: 0
---

# Async Background Tasks

For fire-and-forget background work in async code, use `asyncio.create_task` instead of `Thread(daemon=True)`.

## Pattern

See `packages/erk-slack-bot/src/erk_slack_bot/slack_handlers.py`, grep for `asyncio.create_task` and `run_one_shot_background`.

Key points:
- `asyncio.create_task` replaces `Thread(daemon=True).start()` for fire-and-forget operations
- No daemon flag needed (task lifecycle tied to event loop)
- Naming convention: use "background" suffix for create_task targets (e.g., `run_one_shot_background`)
- Task lifetime: Runs until completion or event loop shutdown
- When to use: Long-running operations that should not block event handler return

## See Also

- [Async Entry Points](async-entry-points.md)
```

---

#### 7. Async entry point pattern

**Location:** `docs/learned/architecture/async-entry-points.md`
**Action:** CREATE
**Source:** [Plan], [Impl]

**Draft Content:**

```markdown
---
description: The async def _run() + asyncio.run() pattern for CLI tools using async libraries
read-when:
  - creating CLI entry points that use async libraries
  - seeing "RuntimeError: no running event loop" errors
  - integrating async libraries with Click commands
tripwires: 1
---

# Async Entry Points

When using async libraries that require a running event loop during instantiation, create a private async function and call it from the synchronous entry point.

## Pattern

See `packages/erk-slack-bot/src/erk_slack_bot/cli.py` for implementation.

```python
async def _run() -> None:
    # Async libraries instantiated HERE, inside event loop
    handler = AsyncSocketModeHandler(app, token)
    await handler.start_async()

def main() -> None:
    asyncio.run(_run())
```

## Common Async Libraries Requiring This Pattern

- `aiohttp.ClientSession`
- `aioboto3` clients
- `AsyncSocketModeHandler` (Slack SDK)
- Database connection pools
- WebSocket clients

## Root Cause

These libraries often create internal resources in `__init__` that call `asyncio.get_running_loop()`. When no event loop is running (before `asyncio.run()`), this raises `RuntimeError: no running event loop`.

## See Also

- [Architecture tripwires](tripwires.md) - tripwire for async library instantiation
```

---

#### 8. Slack AsyncApp migration patterns

**Location:** `docs/learned/integrations/slack-bot-async-patterns.md`
**Action:** CREATE
**Source:** [PR #8039]

**Draft Content:**

```markdown
---
description: Patterns for migrating Slack bots to AsyncApp and AsyncSocketModeHandler
read-when:
  - working with erk-slack-bot package
  - migrating Slack SDK code to async
  - implementing async Slack event handlers
tripwires: 3
---

# Slack AsyncApp Migration Patterns

This documents patterns for using Slack SDK's async interfaces.

## AsyncApp vs App

See `packages/erk-slack-bot/src/erk_slack_bot/app.py` for implementation.

Key points:
- Use `AsyncApp` (from `slack_bolt.async_app`) for async Slack bots
- Use `AsyncSocketModeHandler` (from `slack_bolt.adapter.socket_mode.async_handler`)
- Handler registration via `register_handlers()` remains synchronous
- All event handlers must be `async def`

## AsyncSocketModeHandler Lifecycle

See `packages/erk-slack-bot/src/erk_slack_bot/cli.py`, grep for `_run` and `main`.

- Must instantiate inside async context (inside `asyncio.run()`)
- Use `await handler.start_async()` not `handler.start()`

## Async Handler Chains

See `packages/erk-slack-bot/src/erk_slack_bot/slack_handlers.py`.

All Slack SDK methods require `await` when using AsyncApp:
- `await say(...)`
- `await client.reactions_add(...)`
- `await client.chat_postMessage(...)`
- `await client.chat_update(...)`

Inner helper functions must be `async def` if they call Slack API methods.

## Streaming Callbacks

Breaking change: `on_line` callback signature changed from `Callable[[str], None]` to `Callable[[str], Awaitable[None]]`.

Callbacks must be async if they perform I/O (e.g., calling Slack API).

## Error Handling

Error handling remains identical (SlackApiError try/except pattern unchanged).

## See Also

- [Async Entry Points](../architecture/async-entry-points.md)
```

---

#### 9. Integration tripwires (new file)

**Location:** `docs/learned/integrations/tripwires.md`
**Action:** CREATE
**Source:** [PR #8039]

**Draft Content:**

```markdown
---
description: Tripwires for third-party integration patterns
read-when:
  - integrating third-party async libraries
  - working with Slack SDK
tripwires: 3
---

# Integration Tripwires

## Slack SDK

- **BEFORE using Slack SDK in async code**: Use `AsyncApp` and `AsyncSocketModeHandler` (not App/SocketModeHandler). All event handlers must be `async def`.

- **BEFORE calling Slack SDK methods with AsyncApp**: All methods require `await` (`say`, `client.reactions_add`, `client.chat_postMessage`, `client.chat_update`, etc.)

- **BEFORE passing callbacks to async streaming functions**: Callbacks must be async if they perform I/O. Breaking change: `on_line` signature changed to `Callable[[str], Awaitable[None]]`.
```

---

#### 10. Exit code 124 convention update

**Location:** `docs/learned/architecture/subprocess-wrappers.md`
**Action:** UPDATE
**Source:** [PR #8039]

**Draft Content:**

Add note about exit code 124 convention:

> **Exit Code 124**: Following GNU timeout convention, exit code 124 indicates the subprocess was terminated due to timeout. This applies to both synchronous and asynchronous subprocess execution.

Add cross-reference to `async-subprocess-patterns.md` for async subprocess patterns.

---

### LOW Priority

#### 11. Deprecated loop= parameter removal

**Location:** `docs/learned/architecture/async-subprocess-patterns.md` (subsection)
**Action:** UPDATE (include in async-subprocess-patterns.md)
**Source:** [Plan]

**Draft Content:**

Add subsection:

> **Deprecated loop= Parameter**: Python 3.10+ async libraries are moving away from explicit `loop=` parameter passing. Always instantiate async objects inside a running event loop context rather than passing the loop explicitly. This produces deprecation warnings in older code and outright errors in newer Python versions.

---

#### 12. Async function naming conventions

**Location:** `docs/learned/architecture/async-background-tasks.md` (subsection)
**Action:** UPDATE (include in async-background-tasks.md)
**Source:** [PR #8039]

**Draft Content:**

Already included in async-background-tasks.md draft: naming convention with "background" suffix for create_task targets.

---

#### 13. Update tripwires-index.md for new integrations category

**Location:** `docs/learned/tripwires-index.md`
**Action:** UPDATE
**Source:** [PR #8039]

**Draft Content:**

Add new row to Category Tripwires table:

| Category                                    | Tripwires | Load When Working In                               |
| ------------------------------------------- | --------- | -------------------------------------------------- |
| [integrations](integrations/tripwires.md)   | 3         | Third-party SDK integrations, Slack SDK            |

---

## Contradiction Resolutions

No contradictions found between existing documentation and new insights from this PR.

The existing subprocess documentation (`docs/learned/architecture/subprocess-wrappers.md`) covers synchronous subprocess patterns, while this PR introduces parallel async patterns using `asyncio.create_subprocess_exec`. These are complementary, not contradictory.

---

## Stale Documentation Cleanup

No stale documentation detected. All referenced files in existing docs were verified to exist.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. RuntimeError: no running event loop

**What happened:** `AsyncSocketModeHandler` instantiated in synchronous `main()` before `asyncio.run()` starts event loop. The handler's constructor creates `aiohttp.ClientSession` which requires a running loop.

**Root cause:** Async libraries with constructors that call `asyncio.get_running_loop()` fail when instantiated before the event loop starts.

**Prevention:** Always instantiate async objects inside async functions called by `asyncio.run()`, never in synchronous entry points. Use `async def _run()` + `asyncio.run(_run())` pattern.

**Recommendation:** TRIPWIRE

### 2. Tests passing but runtime failing with async instantiation errors

**What happened:** Mocking `asyncio.run()` prevented real async code execution, so constructor errors in async libraries were not detected during tests.

**Root cause:** Over-aggressive mocking that replaced the entire async runtime rather than specific behaviors.

**Prevention:** Mock specific async behaviors (e.g., `AsyncMock()` on methods) rather than entire `asyncio` module or `asyncio.run()`.

**Recommendation:** TRIPWIRE

### 3. Deprecated loop= parameter in async library calls

**What happened:** Older code passed `loop=` parameter explicitly to async library constructors, which is deprecated in Python 3.10+.

**Root cause:** Libraries moving away from explicit loop passing; modern pattern is to instantiate inside running event loop context.

**Prevention:** Remove `loop=` parameters and ensure instantiation happens inside running event loop context.

**Recommendation:** ADD_TO_DOC (low severity, produces warnings not errors)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. RuntimeError: no running event loop from async library constructors

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before instantiating async libraries (aiohttp.ClientSession, aioboto3, AsyncSocketModeHandler, database clients)
**Warning:** Ensure instantiation happens inside async function called by asyncio.run(), not in synchronous entry points. Use async def _run() + asyncio.run(_run()) pattern.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the error only occurs at runtime (not import time), the fix is non-obvious (restructure entry point), and it affects any code using common async libraries. Without this tripwire, agents may instantiate async objects in synchronous code and only discover the error when running the application.

### 2. Thread+Queue for subprocess streaming

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before using Thread + Queue to stream subprocess output
**Warning:** Use asyncio.create_subprocess_exec with direct readline loop instead. Thread+Queue is an antipattern for async code.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the Thread+Queue pattern appears to work but introduces unnecessary complexity, polling delays, and thread synchronization overhead. Agents trained on older Python patterns may default to this approach. The harm is performance degradation and code complexity.

### 3. subprocess.run in async code

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before calling subprocess.run() or subprocess.Popen() in async code
**Warning:** Use asyncio.create_subprocess_exec to avoid blocking event loop. Synchronous subprocess calls block all async tasks.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because synchronous subprocess calls block the event loop, causing all other async tasks to stall. The code appears to work but has severe performance implications. Without this tripwire, agents may use familiar subprocess.run patterns in async functions.

### 4. AsyncMock for async function testing

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before mocking async functions or testing async code
**Warning:** Use AsyncMock and new_callable=AsyncMock for patches. Use IsolatedAsyncioTestCase for test classes. Use assert_awaited_once() to verify awaiting.
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because using regular `Mock` or `MagicMock` for async functions produces confusing errors or silently fails to verify async behavior. The pattern is pervasive in any async test code.

### 5. Test mock layering (mocking asyncio.run)

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** Before mocking asyncio.run() or entire async runtime in tests
**Warning:** Mock specific async behaviors (methods, functions) instead. Mocking asyncio.run prevents real instantiation and can mask constructor errors.
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because over-aggressive mocking can cause tests to pass while the actual code fails at runtime. This specific error occurred during the implementation sessions and was only caught when running the actual application.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Deprecated loop= parameter in async calls

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Produces deprecation warnings (not silent), but common gotcha in Python 3.10+ migrations. Would warrant promotion if we see more async migrations encountering this issue.

### 2. Async streaming callback signature change

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Breaking change for consumers of streaming APIs. Specific to streaming APIs with callbacks, not broadly applicable. Would warrant promotion if erk exposes more streaming APIs to external consumers.

### 3. Handler registration remains sync

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Specific to Slack SDK AsyncApp. The register_handlers() function is not async even when using AsyncApp. Low general applicability outside Slack integration.
