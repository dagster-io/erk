---
title: Progress Feedback Two-Layer Threading
read_when:
  - "working with progress feedback during LLM calls"
  - "modifying commit message generation"
  - "adding progress indicators to long-running operations"
tripwires:
  - action: "calling time.sleep() or time.monotonic() directly in progress feedback code"
    warning: "Use ctx.time.sleep() and ctx.time.monotonic() for testability. All production call sites pass time=ctx.time."
  - action: "adding a new call site for run_commit_message_generation without time parameter"
    warning: "The time parameter is required for test isolation. Pass time=ctx.time from the ErkContext."
---

# Progress Feedback Two-Layer Threading

A two-layer architecture for providing progress feedback during blocking LLM calls (e.g., PR description generation).

## Problem

LLM calls for PR description generation block for 10-30 seconds with no user feedback. Users need periodic "still waiting" indicators.

## Architecture

### Layer 1: CommitMessageGenerator (Core)

**File:** `src/erk/core/commit_message_generator.py`

The generator runs the LLM call in a background thread and polls with `thread.join(timeout=2.0)`:

- Background thread executes the LLM call
- Main thread polls every 2 seconds (`_PROGRESS_INTERVAL_SECONDS`)
- Yields `ProgressEvent` with elapsed time on each poll
- Yields `CompletionEvent` when thread finishes

Time tracking uses `self._time.monotonic()` from the injected `Time` abstraction.

### Layer 2: run_commit_message_generation() (CLI)

**File:** `src/erk/cli/commands/pr/shared.py`

Wraps the generator in a second producer thread with queue-based event collection:

- Producer thread consumes generator events and puts them on a queue
- Main thread waits on `queue.get(timeout=5.0)` (`_PROGRESS_TIMEOUT_SECONDS`)
- On `queue.Empty`, emits a "Still waiting" message
- Resets elapsed timer on each progress event
- Uses sentinel (`None`) to signal completion

### Why Two Layers

Separation of concerns: the core generator is pure (yields events), while the CLI layer handles presentation (Rich console output, status bars). This keeps the core testable without UI dependencies.

## Production Call Sites

All three call sites pass `time=ctx.time`:

1. `src/erk/cli/commands/pr/submit_pipeline.py` — `generate_description()` step
2. `src/erk/cli/commands/pr/rewrite_cmd.py` — PR rewrite command
3. `src/erk/cli/commands/exec/scripts/update_pr_description.py` — exec script

## Time Abstraction

The `Time` protocol with `FakeTime` enables deterministic testing:

- `time.monotonic()` for elapsed time tracking
- `time.sleep()` for delays
- `FakeTime` provides controlled time for tests (default: `datetime(2024, 1, 15, 14, 30, 0)`)

## Related Documentation

- [Time Injection Testing Patterns](../testing/time-injection-patterns.md) — FakeTime usage in tests
- [Erk Architecture Patterns](erk-architecture.md) — context regeneration and time abstraction
