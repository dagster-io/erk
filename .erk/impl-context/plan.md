# Documentation Plan: Add ErkBot class with streaming agent support and emoji lifecycle management

## Context

This implementation added core infrastructure for streaming agent responses to Slack within the erkbot package. The work introduced the `ErkBot` class wrapping `claude-agent-sdk`, a Slack streaming handler with rate-limited progress updates, emoji reaction functions for lifecycle management, and extended the Time gateway with monotonic clock abstraction for deterministic testing. The implementation also added `@erk chat` command parsing as a parallel path alongside the existing `@erk one-shot` subprocess commands.

Documentation matters here because this work establishes several reusable patterns: frozen dataclass SDK wrappers, gateway ABC extension processes, best-effort operation patterns, and third-party SDK testing strategies. Future agents implementing similar integrations need to understand these patterns to avoid repeating mistakes. The Time gateway extension in particular required 5-place implementation (ABC, Real, Fake, unit tests, and custom test subclasses) which is easy to forget.

Key insights from this implementation include: (1) monotonic clock is semantically different from wall-clock time and acceptable for local performance measurement even without gateway abstraction, (2) test infrastructure can have default parameters even though production code cannot, (3) integration test fixtures in conftest.py are fragile when function signatures change, and (4) custom test subclasses outside the main implementation can break when adding abstract methods to ABCs.

## Raw Materials

PR #8087 and associated session analyses

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 24    |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score 2-3)| 4     |

## Documentation Items

### HIGH Priority

#### 1. Time Gateway Monotonic Clock Extension

**Location:** `docs/learned/architecture/time-gateway.md` (update existing)
**Action:** UPDATE
**Source:** [Impl] Session d5350328

**Draft Content:**

```markdown
## Monotonic Clock Support

The Time gateway now supports monotonic clock for elapsed time measurement.

### When to Use

- **now()**: Wall-clock time for timestamps, logs, persistence
- **monotonic()**: Elapsed time measurement for throttling, timeouts, performance

### Implementation Pattern

See `packages/erk-shared/src/erk_shared/gateway/time/abc.py` for the abstract method.

RealTime wraps `time.monotonic()` directly. FakeTime uses constructor-configured sequences:

```python
# Test with predictable intervals
FakeTime(monotonic_values=[0.0, 2.0, 5.0])  # Returns values in order, repeats last
```

### 5-Place Implementation Requirement

When adding methods to Time ABC, implement in all 5 places:
1. `abc.py` - Abstract method with docstring
2. `real.py` - Production wrapper
3. `fake.py` - Configurable test implementation
4. Unit tests for fake behavior
5. Any custom test subclasses (grep: `class.*Time(` in tests/)
```

#### 2. Integration Test Fixture Signature Drift

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session d5350328

**Draft Content:**

```markdown
## Integration Test Fixture Signature Drift

**Trigger:** When modifying function signatures for dependency injection

**Warning:** Search for conftest.py fixture calls before changing signatures

Integration test fixtures in conftest.py are a common source of breakage when function signatures change. The fixture may be calling the function with the old signature, causing all integration tests to fail at setup.

**Prevention:** Before changing function signatures, run:
```bash
grep -r 'function_name' tests/**/conftest.py
```

**Example:** When `register_handlers()` gained `bot` and `time` parameters, the integration test fixture in `conftest.py` continued calling it without these parameters, breaking all integration tests.
```

#### 3. Custom Test ABC Subclasses

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session d5350328

**Draft Content:**

```markdown
## Custom Test ABC Subclasses

**Trigger:** Before adding abstract method to gateway ABC

**Warning:** Grep for custom test subclasses outside main implementation

When adding an abstract method to a gateway ABC, there may be custom test subclasses (like `ProgressingFakeTime`) that extend the ABC outside the main implementation files. These will break with `TypeError: Can't instantiate abstract class`.

**Prevention:** Before adding abstract method to ABC, run:
```bash
grep -r 'class.*GatewayName(' tests/
```

**Example:** Adding `monotonic()` to Time ABC broke `ProgressingFakeTime` in `test_submit_pr_cache_polling.py` because it inherited from `FakeTime` and didn't implement the new abstract method.
```

#### 4. Resolve Time Module Contradiction

**Location:** `docs/learned/architecture/erk-architecture.md`
**Action:** UPDATE
**Source:** [PR #8087] Review analysis

**Draft Content:**

Update the tripwire at line 18 from:

> "NEVER import time module or calling time.sleep() or datetime.now(). Use context.time.sleep() and context.time.now() for testability."

To:

> "NEVER import time module for testable timing (sleep, timestamps, cross-boundary values). Use Time gateway. **Exception:** `time.monotonic()` is acceptable for local performance measurement that doesn't need test control (e.g., throttling within a single function where the elapsed interval doesn't affect test assertions)."

The distinction is:
- **Local performance measurement** (throttling within a function) - CAN use `time.monotonic()` directly
- **Testable timing** (delays, timestamps, values that cross function boundaries or get persisted) - MUST use Time gateway

#### 5. ErkBot Streaming Architecture

**Location:** `docs/learned/integrations/erkbot-streaming.md`
**Action:** CREATE
**Source:** [Impl] Session 1e0a1dea, [Diff]

**Draft Content:**

```markdown
---
read-when: implementing streaming agent responses in erkbot, working with claude-agent-sdk, building async streaming handlers
tripwires: 0
---

# ErkBot Streaming Architecture

## Overview

ErkBot provides streaming agent responses to Slack users. It wraps `claude-agent-sdk` in a frozen dataclass with deferred execution.

## Core Components

### ErkBot Class

See `packages/erkbot/src/erkbot/agent/bot.py`. Frozen dataclass that stores configuration (model, max_turns, cwd, system_prompt, permission_mode) and exposes `chat_stream()` for streaming.

Key pattern: Defer SDK calls to methods, not `__init__`. This keeps construction lightweight and testable.

### Streaming Handler

See `packages/erkbot/src/erkbot/agent_handler.py`. The `run_agent_background()` function manages the full lifecycle:

1. Post initial status message
2. Add eyes emoji
3. Stream agent events asynchronously
4. Update status message with rate-limited progress
5. Remove eyes emoji, add result emoji (checkmark or X)
6. Post final response or error message

### Rate-Limited Progress Updates

Progress updates use `Time.monotonic()` for throttling to avoid Slack rate limits. Updates are skipped if less than 2 seconds have elapsed since the last update.

### AsyncIterator Pattern

The streaming chain: `claude_agent_sdk.query()` -> `stream_agent_events()` -> async iteration. Yield from inner iterator within outer async generator to avoid premature collection.

## Testing

See `packages/erkbot/tests/test_agent_handler.py`. Uses FakeTime with configured monotonic sequences for deterministic testing of rate-limited behavior.
```

#### 6. Best-Effort Operations Pattern

**Location:** `docs/learned/architecture/best-effort-operations.md`
**Action:** CREATE
**Source:** [PR #8087] Comments analysis

**Draft Content:**

```markdown
---
read-when: implementing non-critical operations that should not fail the parent operation, working with Slack API calls for status updates
tripwires: 0
---

# Best-Effort Operations Pattern

## When to Use

Use this pattern for operations that are "nice to have" but should not cause the parent operation to fail:
- Progress status updates
- Emoji reactions
- Telemetry/analytics calls
- Non-critical notifications

## Implementation

Catch exceptions and either:
1. Log and continue (if logging is available)
2. Silently continue with inline comment explaining why

**Always add an inline comment** explaining that the silent catch is intentional:

```python
try:
    await client.chat_update(channel=channel, ts=status_ts, text=progress)
except SlackApiError:
    pass  # Best-effort: progress update failure should not stop agent execution
```

## When NOT to Use

Do not use for:
- Operations where failure indicates a real problem
- Operations where the user expects confirmation
- Operations that affect correctness of results

## Erkbot Examples

See `packages/erkbot/src/erkbot/agent_handler.py` for progress update catches. Each silent catch has an inline comment explaining the rationale.
```

#### 7. When Mocking is Acceptable

**Location:** `docs/learned/testing/when-mocking-is-acceptable.md`
**Action:** CREATE
**Source:** [PR #8087] Comments analysis, Session d5350328

**Draft Content:**

```markdown
---
read-when: testing code that interfaces with third-party SDKs, deciding between fakes and mocks, writing tests for async dispatch
tripwires: 0
---

# When Mocking is Acceptable

Erk uses fake-driven testing as the default. However, mocking (`@patch`, `AsyncMock`) is acceptable in specific scenarios.

## Acceptable Scenarios

### 1. Third-Party SDK Boundaries

When testing wiring to libraries we don't control (claude-agent-sdk, slack-sdk):

```python
# packages/erkbot/tests/test_bot.py
# Divergence: Using @patch for claude-agent-sdk boundary - cannot use gateway fake
@patch("erkbot.agent.bot.query")
async def test_chat_stream(self, mock_query):
    ...
```

### 2. Async Dispatch Testing

When verifying `asyncio.create_task()` dispatch:

```python
# packages/erkbot/tests/test_slack_handlers.py
# Divergence: Testing async dispatch - verifying create_task is called with correct args
```

## Requirements

1. **Add divergence comment** explaining why mock is used instead of fake
2. **Minimize mock scope** - mock at the boundary, not deep in the stack
3. **Consider gateway fakes first** - if the interface can be abstracted, create a fake

## Erkbot Examples

- `test_bot.py`: Mocks `claude_agent_sdk.query` at SDK boundary
- `test_emoji.py`: Uses `AsyncMock` for Slack client methods
- `test_agent_handler.py`: Uses FakeTime (gateway fake) + mock bot with fake generator
```

---

### MEDIUM Priority

#### 8. Emoji Lifecycle Management

**Location:** `docs/learned/integrations/erkbot-emoji-lifecycle.md`
**Action:** CREATE
**Source:** [Impl] Session 1e0a1dea, [Diff]

**Draft Content:**

```markdown
---
read-when: working with Slack emoji reactions, implementing visual feedback for long-running operations
tripwires: 0
---

# Emoji Lifecycle Management

## Overview

Erkbot uses emoji reactions to provide visual feedback during agent execution:
- Eyes emoji while processing
- Checkmark on success, X on failure

## Implementation

See `packages/erkbot/src/erkbot/emoji.py` for three standalone async functions:
- `add_eyes_emoji()`: Applied at start
- `remove_eyes_emoji()`: Removed after completion
- `add_result_emoji()`: Success/failure signaling

## Idempotent Error Handling

Each function catches `SlackApiError` and ignores known benign errors:
- `already_reacted`: Emoji already present
- `no_reaction`: Emoji already removed
- `missing_scope`: Bot lacks permission
- `not_reactable`: Message type doesn't support reactions

Unexpected errors are re-raised.

## Integration with Finally Block

See `run_agent_background()` in `agent_handler.py`. Emoji cleanup runs in `finally` block to guarantee execution even on exceptions.
```

#### 9. ChatCommand Parser and Dispatch

**Location:** `docs/learned/integrations/erkbot-commands.md`
**Action:** CREATE
**Source:** [Diff]

**Draft Content:**

```markdown
---
read-when: adding new command types to erkbot parser, implementing command dispatch
tripwires: 0
---

# ChatCommand Parser and Dispatch

## Command Model

See `packages/erkbot/src/erkbot/models.py` for `ChatCommand` Pydantic model with `message` field (min_length=1).

## Parser Pattern

See `packages/erkbot/src/erkbot/parser.py`. Pattern: `@erk chat <message>`.
- Empty message returns `None` (forward-compatible for future greeting logic)
- Case-insensitive matching with `(?i)` regex flag

## Dispatch Logic

See `packages/erkbot/src/erkbot/slack_handlers.py`. When `bot is None`, returns "Agent mode is not configured." for graceful degradation.

## Parallel Paths

`@erk chat` (agent-mode) runs alongside `@erk one-shot` (subprocess). Both remain active during migration.
```

#### 10. FakeTime Monotonic Configuration

**Location:** `docs/learned/testing/fake-time-monotonic.md`
**Action:** CREATE
**Source:** [Impl] Session d5350328

**Draft Content:**

```markdown
---
read-when: testing rate-limited operations, testing elapsed time logic, configuring FakeTime for deterministic tests
tripwires: 0
---

# FakeTime Monotonic Configuration

## Constructor Parameter

`FakeTime(monotonic_values: Sequence[float] | None = None)`

Default: `[0.0]` - all calls return 0.0.

## Sequence Behavior

Values are returned in order. When exhausted, last value repeats indefinitely.

```python
fake = FakeTime(monotonic_values=[0.0, 2.0, 5.0])
fake.monotonic()  # 0.0
fake.monotonic()  # 2.0
fake.monotonic()  # 5.0
fake.monotonic()  # 5.0 (repeats)
```

## Use Cases

Testing rate-limited operations:

```python
# Simulate 2-second intervals
FakeTime(monotonic_values=[0.0, 2.0, 4.0, 6.0])
```

Testing timeout scenarios:

```python
# Simulate slow progression that triggers timeout
FakeTime(monotonic_values=[0.0, 1.0, 2.0, 10.0])  # Jump to 10s
```

## Source

See `packages/erk-shared/src/erk_shared/gateway/time/fake.py` for implementation.
```

#### 11. Test Infrastructure Exceptions to Rules

**Location:** `docs/learned/testing/test-infrastructure-exceptions.md`
**Action:** CREATE
**Source:** [PR #8087] Comments analysis

**Draft Content:**

```markdown
---
read-when: writing test fakes, reviewing "no default parameters" violations in test code
tripwires: 0
---

# Test Infrastructure Exceptions

## No-Defaults Rule Exception

The "no default parameters" rule applies to **production APIs**, not test infrastructure.

Test fakes can use sensible defaults to reduce boilerplate:

```python
# Acceptable in test fake
class FakeTime(Time):
    def __init__(
        self,
        *,
        current_time: datetime | None = None,  # OK: test fake
        monotonic_values: Sequence[float] | None = None,  # OK: test fake
    ):
        ...
```

Without defaults, every test would need:

```python
# Verbose without defaults
FakeTime(current_time=DEFAULT_TIME, monotonic_values=[0.0])
```

## Why This Exception Exists

1. Test fakes are internal infrastructure, not public APIs
2. Defaults provide sensible "do nothing special" behavior
3. Test verbosity reduces readability and maintainability

## Scope

This exception applies to:
- Gateway fake constructors (`FakeTime`, `FakeGit`, etc.)
- Test fixture factory functions
- Test helper classes

NOT to:
- Production code
- Code that may be called from production
```

#### 12. Third-Party SDK Error Handling

**Location:** `docs/learned/testing/third-party-sdk-patterns.md`
**Action:** CREATE
**Source:** [PR #8087] Comments analysis

**Draft Content:**

```markdown
---
read-when: handling errors from third-party SDKs, distinguishing LBYL from exception swallowing
tripwires: 0
---

# Third-Party SDK Error Handling

## LBYL with Exception Handlers

Some third-party SDKs don't expose pre-check methods, requiring error code checking within exception handlers. This is NOT "silent exception swallowing" - it's LBYL adapted for SDK limitations.

## Pattern

```python
try:
    await client.reactions_add(...)
except SlackApiError as exc:
    # LBYL: Check specific error codes
    ignored_errors = {"already_reacted", "missing_scope", "not_reactable"}
    if exc.response.get("error") not in ignored_errors:
        raise  # Re-raise unexpected errors
```

## Why This Isn't Swallowing

1. Specific error codes are checked (not blanket `except`)
2. Unexpected errors are re-raised
3. Known benign conditions are documented in the ignored set

## Slack SDK Example

See `packages/erkbot/src/erkbot/emoji.py`. Each emoji function checks Slack-specific error codes and re-raises anything unexpected.
```

#### 13. Parameter Threading for Dependency Injection

**Location:** `docs/learned/integrations/erkbot-parameter-threading.md`
**Action:** CREATE
**Source:** [Impl] Session 1e0a1dea, [Diff]

**Draft Content:**

```markdown
---
read-when: adding new dependencies to erkbot handlers, implementing dependency injection without globals
tripwires: 0
---

# Parameter Threading for Dependency Injection

## Pattern

Thread dependencies through the full call stack via parameters:

```
cli.py -> create_app() -> register_handlers() -> handler closure
```

## Implementation

1. **cli.py**: Constructs dependencies
   ```python
   bot = None  # Node 1.5 will construct from config
   time = RealTime()
   app = create_app(bot=bot, time=time)
   ```

2. **app.py**: Passes through
   ```python
   def create_app(*, bot: ErkBot | None, time: Time) -> App:
       register_handlers(app, bot=bot, time=time)
   ```

3. **slack_handlers.py**: Captures in closure
   ```python
   def register_handlers(app: App, *, bot: ErkBot | None, time: Time):
       @app.event("app_mention")
       async def handle_mention(event, say, client):
           # bot and time captured from enclosing scope
   ```

## None as "Not Configured"

Use `Optional[FeatureClass]` with `None` meaning "feature not configured" (not "missing value"):

```python
if bot is None:
    await say("Agent mode is not configured.")
    return
```

## Testing

Tests pass `FakeTime()` and `bot=None` or a mock bot for deterministic behavior.
```

#### 14. Parameter Shadowing for Gateway Threading

**Location:** `docs/learned/architecture/parameter-shadowing-gateway.md`
**Action:** CREATE
**Source:** [Impl] Session d5350328

**Draft Content:**

```markdown
---
read-when: threading gateway parameters through functions that previously used module imports directly
tripwires: 0
---

# Parameter Shadowing for Gateway Threading

## Pattern

When a function parameter has the same name as an imported module, the parameter shadows the import within function scope.

## Example

```python
import time  # Module import at top

def run_with_throttle(*, time: Time):  # Parameter shadows module
    now = time.monotonic()  # Calls gateway method, not time.monotonic()
```

## Benefits

1. Minimal code changes when introducing gateway
2. Existing `time.xxx()` calls automatically use gateway
3. Clear visual indicator that function uses injected time

## Limitations

If you need both the module AND the gateway in the same function, you must rename one:

```python
import time as time_module

def run(*, time: Time):
    # time_module.monotonic() for direct access
    # time.monotonic() for gateway
```

## When to Use

Prefer this pattern when:
- Converting existing code to use gateways
- The function only needs gateway methods, not module functions
```

#### 15. Progressive Code Simplification

**Location:** `docs/learned/documentation/progressive-simplification.md`
**Action:** CREATE
**Source:** [PR #8087] Comments analysis

**Draft Content:**

```markdown
---
read-when: simplifying complex expressions during code review, converting ternaries to LBYL
tripwires: 0
---

# Progressive Code Simplification

## Pattern

Complex expressions can be simplified iteratively:

1. **Initial**: Clever but dense
   ```python
   return self._monotonic_values[min(self._monotonic_index, len(self._monotonic_values) - 1)]
   ```

2. **Intermediate**: Clearer conditional
   ```python
   if self._monotonic_index < len(self._monotonic_values):
       return self._monotonic_values[self._monotonic_index]
   return self._monotonic_values[-1]
   ```

3. **Final**: LBYL with explicit intent
   ```python
   idx = self._monotonic_index
   if idx >= len(self._monotonic_values):
       idx = len(self._monotonic_values) - 1
   return self._monotonic_values[idx]
   ```

## Why Simplify

- Easier debugging (can set breakpoints on individual lines)
- Clearer intent for future readers
- Matches LBYL preference in erk codebase

## Automated Reviewers

The dignified-python-reviewer may flag complex expressions. Each iteration makes the code more accessible.
```

#### 16. Workspace Package Dependencies

**Location:** `docs/learned/architecture/workspace-package-dependencies.md`
**Action:** CREATE
**Source:** [Impl] Session d5350328, [Diff]

**Draft Content:**

```markdown
---
read-when: adding cross-package dependencies within the erk workspace, sharing code between erk and erkbot
tripwires: 1
---

# Workspace Package Dependencies

## Adding a Workspace Dependency

To add `erk-shared` as dependency of `erkbot`:

1. In `packages/erkbot/pyproject.toml`:
   ```toml
   dependencies = [
       "erk-shared",
       ...
   ]

   [tool.uv.sources]
   erk-shared = { workspace = true }
   ```

2. Run `uv sync --package erkbot` to install

## Tripwire: Package Disappears After Sync

After modifying pyproject.toml, `uv sync` may uninstall the workspace package but not reinstall it.

**Fix:** Run `uv sync --package <package-name>` explicitly.

## When to Share vs Duplicate

**Share** (via erk-shared):
- Gateway abstractions (Time, Git, Env)
- Core types used across packages
- Utilities with no package-specific dependencies

**Duplicate**:
- Small utilities specific to one package
- Types that would create circular dependencies
```

---

### LOW Priority

#### 17. Test Assertions Anti-Patterns

**Location:** `docs/learned/testing/test-assertions.md`
**Action:** CREATE
**Source:** [PR #8087] Comments analysis

**Draft Content:**

```markdown
---
read-when: writing test assertions, reviewing redundant checks
tripwires: 0
---

# Test Assertions Anti-Patterns

## Redundant assertIsInstance + isinstance

`unittest.assertIsInstance()` already validates type. Follow-up `assert isinstance()` is redundant:

```python
# Anti-pattern
self.assertIsInstance(result, ChatCommand)
assert isinstance(result, ChatCommand)  # Redundant

# Correct
self.assertIsInstance(result, ChatCommand)
self.assertEqual(result.message, expected_message)
```

The second `isinstance` check was likely added for type narrowing, but the test already confirmed the type.
```

#### 18. Automated Reviewer Types

**Location:** `docs/learned/ci/automated-reviewers.md`
**Action:** CREATE
**Source:** [PR #8087] Comments analysis

**Draft Content:**

```markdown
---
read-when: understanding PR review bot comments, addressing automated review feedback
tripwires: 0
---

# Automated Reviewer Types

## Four Reviewer Types

1. **Dignified Python Reviewer**: Checks coding standards (LBYL, no defaults, etc.)
2. **Test Coverage Reviewer**: Verifies test presence for new code
3. **Code Simplifier**: Suggests expression simplifications
4. **Tripwires Reviewer**: Checks for pattern violations documented in tripwires

## Activity Log Tracking

Each reviewer tracks its activity across iterations:

```
## Activity Log
- **Round 1**: 3 comments (2 suggestions, 1 must-fix)
- **Round 2**: 1 comment (false positive resolved via explanation)
```

## Handling False Positives

Some comments are false positives. When the existing code is correct:
1. Reply with explanation of why the pattern is appropriate
2. Mark thread as resolved
3. Do NOT make unnecessary changes to appease the bot
```

#### 19. ErkBot Migration Strategy

**Location:** `docs/learned/integrations/erkbot-migration-strategy.md`
**Action:** CREATE
**Source:** [Diff]

**Draft Content:**

```markdown
---
read-when: understanding erkbot command evolution, planning new erkbot features
tripwires: 0
---

# ErkBot Migration Strategy

## Parallel Command Paths

Two command paths coexist during migration:
- `@erk one-shot <prompt>`: Subprocess-based (original)
- `@erk chat <prompt>`: Agent-mode (new, via ErkBot)

## Current State

`bot=None` in cli.py means agent mode is not yet configured. ChatCommand returns "Agent mode is not configured."

## Future Nodes

- **Node 1.4**: Add config fields (ANTHROPIC_API_KEY, ERK_REPO_PATH, ERK_MODEL)
- **Node 1.5**: CLI wiring - construct ErkBot from Settings
- **Node 6.1**: Remove subprocess modules, consolidate features

## Testing Strategy

Integration tests pass `bot=None, time=FakeTime()` to test the unconfigured state. Future tests will use mock or fake ErkBot instances.
```

#### 20. Update Branch Manager Patterns

**Location:** `docs/learned/architecture/branch-manager-patterns.md`
**Action:** UPDATE
**Source:** [Impl] Session 70634429

**Draft Content:**

Add section:

```markdown
## GraphiteBranchManager Automatic Tracking

`create_branch()` handles Graphite stack tracking internally. Do not call `track_branch()` separately after `create_branch()`.

The method:
1. Creates git branch
2. Calls Graphite tracking with the base_branch parameter
3. Returns success/failure

Over-tracking (calling track_branch after create_branch) is harmless but redundant.
```

#### 21. Update Planning Tripwires

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 70634429

**Draft Content:**

Add tripwire:

```markdown
## Plan Branch Parent Detection

**Trigger:** When implementing plan-save

**Warning:** Detect current branch context; don't hardcode origin/trunk as base

Plan branches should be created:
- Off the current feature branch when running on a feature branch
- Off trunk when running on trunk

Reading parent from current checkout context at checkout time (not save time) creates fragile cross-worktree behavior.
```

#### 22. Update Testing Documentation

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Diff]

**Draft Content:**

Add to existing testing patterns:

```markdown
## AsyncMock for Async Operations

Use `unittest.mock.AsyncMock` for mocking async methods in unit tests:

```python
mock_client = MagicMock()
mock_client.reactions_add = AsyncMock()
```

See `when-mocking-is-acceptable.md` for guidance on when mocking vs fakes is appropriate.
```

#### 23. Update Dependency Injection Doc

**Location:** `docs/learned/architecture/dependency-injection.md`
**Action:** UPDATE
**Source:** [Diff]

**Draft Content:**

Add erkbot as exemplar:

```markdown
## Erkbot Exemplar

See `packages/erkbot/` for a complete example of dependency injection without globals:

- `cli.py`: Constructs `RealTime()`, passes to `create_app()`
- `app.py`: Threads `time` parameter to `register_handlers()`
- `slack_handlers.py`: Captures `time` in handler closure
- `agent_handler.py`: Uses injected `time.monotonic()` for throttling

Tests inject `FakeTime()` for deterministic behavior.
```

#### 24. Update Conventions for SDK Wrappers

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [Impl] Session 1e0a1dea

**Draft Content:**

Add to frozen dataclass section:

```markdown
## SDK Wrapper Pattern

When wrapping third-party SDKs, use frozen dataclass with deferred execution:

- Store configuration fields only
- Defer SDK calls to methods, not `__init__`
- This keeps construction lightweight and testable

See `packages/erkbot/src/erkbot/agent/bot.py` for `ErkBot` as exemplar.
```

---

## Contradiction Resolutions

### 1. Time Module Usage vs Time Gateway Abstraction

**Existing doc:** `docs/learned/architecture/erk-architecture.md` (tripwire line 18)
**Conflict:** The tripwire prohibits all `time` module usage, but `time.monotonic()` for local performance measurement (throttling) was correctly used in agent_handler.py without gateway abstraction initially.

**Resolution:** Update the existing tripwire to clarify:
- `time.monotonic()` is acceptable for local performance measurement that doesn't need test control
- Time gateway is required when tests need to control time passage, need deterministic timestamps, or when time values cross function boundaries

The PR ultimately threaded the Time gateway for consistency, but the original direct usage was valid. The documentation should acknowledge both approaches.

---

## Stale Documentation Cleanup

No stale documentation detected. All existing documentation references were verified against the current codebase. The existing-docs-checker found zero phantom references.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Abstract Method Addition Breaks Custom Test Classes

**What happened:** Adding `monotonic()` to Time ABC broke `ProgressingFakeTime` in `test_submit_pr_cache_polling.py` with `TypeError: Can't instantiate abstract class`.

**Root cause:** The test file had a custom subclass of `FakeTime` that didn't implement the new abstract method. This subclass wasn't discovered during the standard grep for implementation files.

**Prevention:** Before adding abstract method to ABC, grep for ALL classes that inherit from it, including test-only subclasses: `grep -r 'class.*Time(' tests/`

**Recommendation:** TRIPWIRE (score 5)

### 2. Integration Test Fixture Signature Drift

**What happened:** After adding `bot` and `time` parameters to `register_handlers()`, all integration tests failed at setup with `TypeError: register_handlers() got unexpected keyword argument`.

**Root cause:** The fixture in `tests/integration/conftest.py` was calling `register_handlers()` with the old signature. Function signature changes don't automatically update fixture calls.

**Prevention:** When modifying function signatures, search conftest.py files: `grep -r 'function_name' tests/**/conftest.py`

**Recommendation:** TRIPWIRE (score 6)

### 3. Workspace Package Disappears After Dependency Change

**What happened:** After adding `erk-shared` dependency to erkbot's pyproject.toml, running `uv sync` uninstalled erkbot but didn't reinstall it.

**Root cause:** uv's sync command uninstalled the package when dependencies changed but didn't automatically reinstall workspace packages.

**Prevention:** After modifying workspace package dependencies, explicitly sync: `uv sync --package <package-name>`

**Recommendation:** ADD_TO_DOC (medium severity, easy fix)

### 4. Bot Review False Positives

**What happened:** Automated reviewers flagged several items that were actually correct:
- FakeTime default parameters (test infrastructure exception)
- emoji.py exception handling (proper LBYL with error code checking)

**Root cause:** Automated rules don't account for documented exceptions.

**Prevention:** Document test infrastructure exceptions and LBYL patterns that may appear to violate rules.

**Recommendation:** ADD_TO_DOC (clarification for future reviews)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Time Gateway ABC Extension

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before adding methods to Time ABC

**Warning:** Implement in all 5 places: abc.py (abstract), real.py (wrapper), fake.py (configurable), unit tests, integration tests. Also grep for custom test subclasses: `grep -r 'class.*Time(' tests/`

**Target doc:** `docs/learned/architecture/tripwires.md`

Adding a method to the Time ABC without implementing it everywhere causes TypeError at runtime, not at import time. The error only manifests when the specific class is instantiated, which may be in an obscure test. Custom test subclasses outside the main implementation files are particularly easy to miss.

### 2. Integration Test Fixture Signature Drift

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive +2)

**Trigger:** When modifying function signatures for dependency injection

**Warning:** Search for conftest.py fixture calls: `grep -r 'function_name' tests/**/conftest.py`

**Target doc:** `docs/learned/testing/tripwires.md`

Function signature changes in core functions (especially those called from conftest.py fixtures) break all integration tests simultaneously. The failure happens at test setup, not at the specific test, making the root cause non-obvious.

### 3. Custom Test ABC Subclasses

**Score:** 5/10 (Non-obvious +2, Destructive +2, Cross-cutting +1)

**Trigger:** Before adding abstract method to gateway ABC

**Warning:** Grep for custom test subclasses outside main implementation: `grep -r 'class.*GatewayName(' tests/`

**Target doc:** `docs/learned/architecture/tripwires.md`

Test files may contain custom subclasses of gateway fakes (like `ProgressingFakeTime` extending `FakeTime`) that need to implement new abstract methods. These are outside the standard implementation files and easy to miss.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Plan Branch Parent Detection

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)

**Notes:** Documented in session 70634429. The issue is specific to plan-save workflows and may not recur frequently. Watch for additional incidents before elevating to tripwire.

### 2. GraphiteBranchManager Over-Tracking

**Score:** 2/10 (Non-obvious +2)

**Notes:** Low severity - calling track_branch after create_branch is harmless but redundant. Not destructive enough to warrant tripwire.

### 3. uv sync --package After Dependency Changes

**Score:** 3/10 (Non-obvious +2, External tool +1)

**Notes:** Medium severity - package disappears but error is clear and fix is simple. Consider tripwire if this recurs multiple times.

### 4. Long Line After Inline Conditional

**Score:** 1/10 (Low severity)

**Notes:** Caught by linter automatically. No tripwire needed.

---

## Code Change Items

### 1. Ignored Error Sets as Typed Constant

**Location:** `packages/erkbot/src/erkbot/emoji.py`
**Action:** CODE_CHANGE

**What to add:** Create a typed constant for the ignored error set:

```python
IGNORED_SLACK_ERRORS: set[str] = {
    "already_reacted",
    "no_reaction",
    "missing_scope",
    "not_reactable",
}
```

**Why:** The error set is currently duplicated across emoji functions. A constant makes it discoverable, testable, and ensures consistency. This follows the "cornerstone test" principle - enumerable catalogs should be in code, not docs.

**Where:** At module level in `emoji.py`, before the function definitions.
