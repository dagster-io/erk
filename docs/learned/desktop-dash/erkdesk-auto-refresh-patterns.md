---
title: Erkdesk Auto-Refresh Patterns
read_when:
  - "building auto-refreshing UI components in erkdesk"
  - "implementing periodic data fetching with React"
  - "managing URL loading to avoid redundant IPC calls"
  - "debugging duplicate webview loads or refresh issues"
category: desktop-dash
tripwires:
  - action: "loading URLs on every render without deduplication"
    warning: "Use useRef to track lastLoadedUrl. Compare url !== lastLoadedUrlRef.current before calling loadWebViewURL() to prevent redundant IPC calls."
  - action: "replacing good data with error states during refresh"
    warning: "Return early from refresh on error (if (!result.success) return). Keep showing last good data instead of empty state."
  - action: "updating state directly instead of using functional setState"
    warning: "Use setPlans((prevPlans) => ...) and setSelectedIndex((prevIndex) => ...) to ensure reading latest state when multiple updates are queued."
  - action: "forgetting to return cleanup function from useEffect intervals"
    warning: "Always return () => clearInterval(intervalId) from useEffect to prevent memory leaks and multiple intervals running."
---

# Erkdesk Auto-Refresh Patterns

## Overview

The erkdesk dashboard auto-refreshes the plan list every 15 seconds, preserving user selection and avoiding redundant operations.

**Architecture:** `App.tsx` owns all state, `PlanList.tsx` is presentation-only (props, no state).

## Core Pattern

**File:** `erkdesk/src/renderer/App.tsx`

### 1. Refresh Interval

```typescript
const REFRESH_INTERVAL_MS = 15_000;

useEffect(() => {
  const intervalId = setInterval(() => {
    window.erkdesk.fetchPlans().then((result) => {
      if (!result.success) return; // Silent failure - don't replace good data
      setPlans((prevPlans) => {
        const newPlans = result.plans;
        setSelectedIndex((prevIndex) => {
          // Selection preservation logic (see Step 2)
        });
        return newPlans;
      });
    });
  }, REFRESH_INTERVAL_MS);
  return () => clearInterval(intervalId); // Cleanup on unmount
}, []);
```

**Key decisions:**

- **15 seconds:** Balance between freshness and API load
- **Silent error handling:** If refresh fails, keep showing the last good data (don't show error state)
- **Empty dependency array:** Interval runs for the lifetime of the component

### 2. Selection Preservation Across Refresh

Uses [Selection Preservation by Value](../architecture/selection-preservation-by-value.md) pattern:

```typescript
setSelectedIndex((prevIndex) => {
  const previousIssueNumber = prevPlans[prevIndex]?.issue_number;
  if (previousIssueNumber === undefined) return 0;
  const newIndex = newPlans.findIndex(
    (p) => p.issue_number === previousIssueNumber,
  );
  return newIndex >= 0 ? newIndex : 0;
});
```

**Why functional setState:**

- `setPlans((prevPlans) => ...)` ensures we read the latest plans
- `setSelectedIndex((prevIndex) => ...)` ensures we read the latest index
- Prevents race conditions when multiple state updates are queued

### 3. URL Deduplication with useRef

**Problem:** Without deduplication, every selection change or refresh triggers an IPC call to load the URL, even if it's already loaded.

**Solution:** Track the last loaded URL with `useRef`:

```typescript
const lastLoadedUrlRef = useRef<string | null>(null);

useEffect(() => {
  if (selectedIndex < 0 || selectedIndex >= plans.length) return;
  const plan = plans[selectedIndex];
  const url = plan.pr_url ?? plan.issue_url;
  if (url && url !== lastLoadedUrlRef.current) {
    lastLoadedUrlRef.current = url;
    window.erkdesk.loadWebViewURL(url);
  }
}, [selectedIndex, plans]);
```

**Why useRef:**

- `useRef` persists across renders without triggering re-renders
- Comparing `url !== lastLoadedUrlRef.current` prevents redundant IPC calls
- Works correctly even when selection jumps between the same URL (e.g., two PRs for the same issue)

**Why this effect depends on both `selectedIndex` and `plans`:**

- `selectedIndex` change: User navigated to a different row
- `plans` change: Data refreshed, the plan at `selectedIndex` might have a new URL (e.g., PR opened)

### 4. URL Priority

```typescript
const url = plan.pr_url ?? plan.issue_url;
```

**Decision:** Prefer PR URL over issue URL when both exist.

**Rationale:**

- PR shows the implementation (code diff, review comments)
- Issue shows the plan (markdown, discussion)
- If a PR exists, the user likely wants to review the implementation

### 5. LBYL Bounds Checking Before IPC

```typescript
if (selectedIndex < 0 || selectedIndex >= plans.length) return;
```

**Always verify bounds before accessing arrays or making IPC calls.**

This prevents:

- Accessing `plans[selectedIndex]` when `selectedIndex === -1` (initial state)
- Accessing `plans[selectedIndex]` after all plans are removed
- Sending invalid data to the main process

## Component Hierarchy

**App.tsx:**

- Owns all state (`plans`, `selectedIndex`, `loading`, `error`)
- Handles data fetching and refresh
- Manages keyboard navigation (`j/k`, arrow keys)
- Loads URLs into webview

**PlanList.tsx:**

- Receives props: `plans`, `selectedIndex`, `onSelectIndex`, `loading`, `error`
- Renders the table
- Calls `onSelectIndex` when user clicks a row
- **No internal state, no effects, no IPC calls**

**Why this split:**

- State management is centralized (easier to debug)
- PlanList is a pure presentation component (easier to test)
- URL loading logic doesn't need to know about the table rendering

## Related Patterns

- [Selection Preservation by Value](../architecture/selection-preservation-by-value.md) - How selection survives refresh
- [Textual Quirks: clear() Resets Cursor Position](../textual/quirks.md#clear-resets-cursor-position) - Python equivalent pattern

## Testing Considerations

**For auto-refresh with fake timers, see:**

- [Vitest Fake Timers with Promises](../testing/vitest-fake-timers-with-promises.md)

**Key points:**

- Use `vi.advanceTimersByTimeAsync()` to advance time and flush Promises
- Always clean up with `vi.useRealTimers()` in `afterEach`
- Mock `window.erkdesk.fetchPlans()` to return controlled data
