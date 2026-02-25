---
title: Async Action Refresh Pattern
read_when:
  - "adding background operations to the TUI"
  - "implementing worker thread actions in the dashboard"
  - "refreshing TUI data after a background subprocess"
tripwires:
  - action: "completing a background worker thread without calling action_refresh"
    warning: "Always call_from_thread(self.action_refresh) after successful background work to update the TUI display."
    score: 6
  - action: "passing --no-wait in worker thread subprocess calls"
    warning: "Never pass --no-wait in worker threads — it defeats the polling purpose. The thread exists to wait for the operation to complete before refreshing."
    score: 5
---

# Async Action Refresh Pattern

The TUI dashboard uses `@work(thread=True)` decorated methods to run subprocess operations in background threads without blocking the UI. After each successful operation, the thread triggers a data refresh.

## The Pattern

<!-- Source: src/erk/tui/app.py, _address_remote_async -->

All background worker methods in `app.py` follow the same structure:

1. **Decorate with `@work(thread=True)`** — Textual runs the method in a worker thread
2. **Run subprocess** — Execute the CLI command (e.g., `erk pr address-remote`)
3. **Show success toast** — `self.call_from_thread(self.notify, message)`
4. **Trigger refresh** — `self.call_from_thread(self.action_refresh)`
5. **Handle errors** — Catch `CalledProcessError`, show error toast

## Implementations

<!-- Source: src/erk/tui/app.py, _close_plan_async -->

The pattern is used consistently across multiple async operations in `app.py`, including methods for closing plans, dispatching PR address workflows, landing PRs, submitting to the implementation queue, closing objectives, and dispatching one-shot plans. All follow the same structure and call `self.call_from_thread(self.action_refresh)` after the subprocess succeeds.

## Why call_from_thread

Textual's `@work(thread=True)` runs the method in a separate thread. Direct attribute access on the app from a worker thread would cause threading issues. `call_from_thread()` schedules the call on the main event loop thread.

## Anti-Patterns

**Missing refresh after success:** Forgetting `call_from_thread(self.action_refresh)` means the TUI shows stale data until the next manual refresh or timer tick.

**Using --no-wait in worker threads:** The worker thread exists specifically to wait for the operation to complete. Passing `--no-wait` causes the thread to return immediately without refreshing meaningful state changes.

## Related Documentation

- [Visual Status Indicators](../desktop-dash/visual-status-indicators.md) — What the refreshed data displays
