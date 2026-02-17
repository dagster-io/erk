---
title: TUI Async State Snapshot Pattern
category: tui
read_when:
  - "adding async data fetching to the TUI"
  - "reading self._view_mode during async operations"
  - "debugging stale data appearing in the wrong tab"
tripwires:
  - action: "reading self._view_mode during async data fetch without snapshotting"
    warning: "Snapshot at fetch start with fetched_mode = self._view_mode. Read this doc."
  - action: "caching fetched data under self._view_mode after an async operation"
    warning: "Cache under fetched_mode (snapshot at start), not self._view_mode (may have changed during fetch)."
---

# TUI Async State Snapshot Pattern

When fetching data asynchronously in the TUI, the user may switch views during the fetch. The "fetched mode" pattern prevents race conditions by snapshotting the active view at fetch start and threading it through the pipeline.

## The Problem

```
1. User is on Plans tab, fetch starts
2. User switches to Objectives tab during fetch
3. Fetch completes with Plans data
4. BUG: Plans data overwrites Objectives display
```

Without snapshotting, `self._view_mode` reflects the _current_ view (Objectives), but the fetched data belongs to the _original_ view (Plans). Caching under the wrong key or updating the wrong display corrupts the UI.

## The Solution: `fetched_mode` Snapshot

<!-- Source: src/erk/tui/app.py, _load_data lines 166-209 -->

At the start of `_load_data()`, snapshot the current view:

```python
fetched_mode = self._view_mode
```

Thread `fetched_mode` through the entire pipeline:

1. **Fetch**: Use `fetched_mode` for query parameters (labels, filters)
2. **Cache**: Store results under `fetched_mode`'s labels (always correct)
3. **Display**: Only update the display if `fetched_mode == self._view_mode`

## Cache Correctness vs Display Correctness

These are separate concerns:

- **Cache**: Always store under `fetched_mode`'s labels. The data was fetched for that view, so it belongs in that cache slot regardless of what the user is currently looking at.
- **Display**: Only update if the current view still matches `fetched_mode`. Otherwise, the user has already moved on and the display should not be touched.

<!-- Source: src/erk/tui/app.py, _update_table lines 229-235 -->

In `_update_table()`, the cache is written under the **fetched** view's labels (always correct regardless of current view), and the display is only updated if the user hasn't switched tabs during the fetch. See `src/erk/tui/app.py:229-235` for the implementation.

## When To Apply This Pattern

Apply the snapshot pattern whenever:

- An async operation reads mutable state (like `_view_mode`) that could change during execution
- The result needs to be stored or displayed based on the state at fetch start, not at completion
- Multiple concurrent fetches could race (e.g., rapid tab switching)

## Implementation Reference

| Component         | File                                   | Lines   |
| ----------------- | -------------------------------------- | ------- |
| Snapshot creation | `src/erk/tui/app.py` (`_load_data`)    | 171-175 |
| Cache storage     | `src/erk/tui/app.py` (`_update_table`) | 229-231 |
| Display guard     | `src/erk/tui/app.py` (`_update_table`) | 233-235 |
