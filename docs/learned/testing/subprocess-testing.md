---
title: Subprocess Testing Patterns
read_when:
  - "testing code that uses subprocess"
  - "creating fakes for process execution"
  - "avoiding subprocess mocks in tests"
last_audited: "2026-02-05 00:00 PT"
audit_result: edited
---

# Subprocess Testing Patterns

Patterns for testing code that executes subprocesses, emphasizing fake-driven testing over mocking.

## Core Principle: Fakes Over Mocks

**Never mock subprocess directly.** Instead, use the gateway abstraction pattern:

1. Define an ABC for the capability
2. Implement a Real class using subprocess
3. Implement a Fake class that simulates behavior in-memory
4. Inject the appropriate implementation

This provides predictable tests, fast execution (no real processes), readable test intent, and realistic edge case simulation.

## Key Fakes

### FakePromptExecutor

Simulates Claude CLI execution. Configurable via constructor for: availability, command failure, PR creation simulation, zero-turn hook blocking, streaming events.

- **Source**: `tests/fakes/prompt_executor.py`
- **Tracking**: `executed_commands` property records all calls for assertions
- **Events**: Yields `ToolEvent`, `ProcessErrorEvent`, `NoOutputEvent`, `ErrorEvent` as configured

### FakeCIRunner

Simulates CI check execution (pytest, ruff, prettier, etc.). Configurable via constructor for specific check failures and missing commands.

- **Source**: `packages/erk-shared/src/erk_shared/gateway/ci_runner/fake.py`
- **Factory**: `FakeCIRunner.create_passing_all()` for the common success case
- **Tracking**: `run_calls` and `check_names_run` properties for assertions
- **Result**: `CICheckResult` with `passed` (bool) and `error_type` (`"command_not_found"`, `"command_failed"`, or None)

## Integration Tests

When real subprocess execution is needed, use `tests/integration/`. These tests accept longer run times and require real tools in the CI environment.

## Related Documentation

- [Erk Test Reference](testing.md) — Overall testing patterns
- [Subprocess Wrappers](../architecture/subprocess-wrappers.md) — Wrapper function patterns
- [Monkeypatch Elimination](monkeypatch-elimination-checklist.md) — Migration checklist
