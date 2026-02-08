---
title: Erkdesk Auto-Refresh Patterns
read_when:
  - "building auto-refreshing UI components in erkdesk"
  - "adding periodic data fetching with IPC-backed webview loading"
  - "debugging duplicate webview loads or stale data after refresh"
category: desktop-dash
tripwires:
  - action: "loading URLs on every render without deduplication"
    warning: "Use useRef to track lastLoadedUrl. Compare against ref before calling loadWebViewURL() — IPC calls are expensive and cause visible webview flicker."
  - action: "replacing good data with error states during refresh"
    warning: "Return early from refresh on error. Keep showing last good data instead of flashing an error state that auto-resolves on next successful refresh."
  - action: "updating state directly instead of using functional setState in interval callbacks"
    warning: "Interval closures capture stale state. Use functional setState (setPrevState => ...) to read latest values inside setInterval callbacks."
  - action: "forgetting to return cleanup function from useEffect intervals"
    warning: "Always return () => clearInterval(intervalId) from useEffect to prevent multiple intervals running simultaneously."
---

# Erkdesk Auto-Refresh Patterns

## Why This Document Exists

The erkdesk refresh cycle coordinates four concerns that interact in non-obvious ways: periodic fetching, selection preservation, IPC deduplication, and error resilience. Each is simple alone, but getting them wrong in combination causes bugs like cursor jumping, webview flickering, stale data display, or leaked intervals. This document explains the design decisions connecting them.

## Architecture Decision: State Ownership Split

<!-- Source: erkdesk/src/renderer/App.tsx, App component -->
<!-- Source: erkdesk/src/renderer/components/PlanList.tsx, PlanList component -->

App.tsx owns all state and side effects (fetching, intervals, URL loading, keyboard navigation). PlanList is a pure presentation component with no internal state, no effects, and no IPC calls.

**Why this split matters for auto-refresh:** Centralizing state in App means the refresh interval only needs to coordinate with one component. If PlanList owned selection state, the refresh callback would need to reach across component boundaries to preserve selection — a much harder coordination problem.

## The Refresh Coordination Problem

The refresh interval in App.tsx (see the second `useEffect` with `setInterval`) must solve four problems simultaneously:

### 1. Silent Error Recovery

**Decision:** Refresh errors are silently dropped — the user keeps seeing the last good data.

**Why not show errors during refresh?** The initial load shows errors (user needs to know the system is broken). But mid-session refresh failures are transient — network blips, backend restarts. Flashing an error state that auto-resolves 15 seconds later is worse UX than showing slightly stale data. The early return on `!result.success` is the entire error strategy.

### 2. Functional setState Inside Closures

**Why functional setState is mandatory here (not just a best practice):** The `setInterval` callback captures a stale closure. Without functional updates, the callback would read `plans` and `selectedIndex` from the render where the interval was created — always the initial empty state. Functional setState (`setPlans((prevPlans) => ...)`) reads the actual current value at update time, not the captured closure value.

This is the most common source of bugs when adding refresh logic: everything works on first render but the interval callback "can't see" subsequent state changes.

### 3. Selection Preservation Across Refresh

Uses the [Selection Preservation by Value](../architecture/selection-preservation-by-value.md) pattern. The key implementation detail specific to this refresh cycle: the `setSelectedIndex` call is _nested inside_ the `setPlans` updater function. This ensures `prevPlans` (needed to look up the current selection's `issue_number`) is available in the same closure where `newPlans` is being set.

Nesting `setSelectedIndex` inside `setPlans`'s updater is unusual — it works because React allows calling state setters inside other state setter callbacks. The alternative (separate effects) would introduce a render frame where `selectedIndex` points to a stale array, causing a flash of wrong selection.

### 4. URL Deduplication via useRef

<!-- Source: erkdesk/src/renderer/App.tsx, lastLoadedUrlRef usage -->

The URL-loading effect depends on both `selectedIndex` and `plans`. This means it fires on every refresh even if the selection hasn't changed, because `plans` is a new array reference each time. Without deduplication, the webview would reload the same GitHub page every 15 seconds, causing visible flicker.

**Why useRef instead of useMemo or state:** The deduplication check is a side-effect gate, not derived state. `useRef` persists without triggering re-renders and without appearing in the dependency array — exactly the semantics needed for "remember what we last did."

**Why the effect needs both dependencies:** `selectedIndex` changes on user navigation (load new URL). `plans` changes on refresh (the plan at the same index might now have a PR URL where it previously only had an issue URL). Either change can produce a new URL to load.

## URL Priority Decision

**PR URL is preferred over issue URL** when both exist. The rationale: once a PR exists, the user's workflow shifts from reviewing the plan to reviewing the implementation. The issue (plan) is still accessible via the PR description link.

## Anti-Patterns

**Debouncing instead of deduplication:** Debounce delays the load but doesn't prevent redundant loads of the same URL. The ref-based approach is both faster (no delay) and more correct (truly deduplicates).

**Using useEffect dependencies for deduplication:** Adding `url` as a dependency and removing `selectedIndex`/`plans` seems cleaner but breaks when the URL doesn't change but the plan data does (e.g., PR status update needs no URL reload but does need data propagation).

**Showing loading spinners during refresh:** The initial load shows a loading state because there's nothing else to display. During refresh, showing a spinner replaces useful content with a blank state — the opposite of helpful.

## Related Patterns

- [Selection Preservation by Value](../architecture/selection-preservation-by-value.md) — The general pattern; this doc covers its specific integration with the refresh cycle
- [Vitest Fake Timers with Promises](../testing/vitest-fake-timers-with-promises.md) — Testing the refresh interval requires async timer advancement
- [Textual Quirks](../textual/quirks.md) — Python/Textual equivalent of the selection preservation problem
