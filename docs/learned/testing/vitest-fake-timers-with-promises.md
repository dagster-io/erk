---
title: Vitest Fake Timers with Promises
read_when:
  - "testing React components with setInterval or setTimeout"
  - "using Vitest fake timers with async/await code"
  - "debugging tests that hang when advancing fake timers"
  - "testing auto-refresh patterns in React"
category: testing
tripwires:
  - action: "using vi.advanceTimersByTime() with Promise-based code"
    warning: "Use await vi.advanceTimersByTimeAsync() instead. Synchronous advancement blocks Promise microtasks and causes test hangs."
  - action: "forgetting vi.useRealTimers() in afterEach()"
    warning: "Always restore real timers in afterEach(). Fake timers persist across tests and cause unpredictable failures."
  - action: "forgetting shouldAdvanceTime option when manually advancing"
    warning: "Use vi.useFakeTimers({ shouldAdvanceTime: true }) to enable manual timer control with advanceTimersByTimeAsync()."
---

# Vitest Fake Timers with Promises

## Problem

When testing code that uses `setInterval` with async operations (like API calls), fake timers can block Promise microtasks. This causes tests to hang or fail unpredictably.

**Example scenario:**

```typescript
// Component code
useEffect(() => {
  const intervalId = setInterval(() => {
    window.erkdesk.fetchPlans().then((result) => {
      // This Promise callback never fires with regular fake timers
      setPlans(result.plans);
    });
  }, 15_000);
  return () => clearInterval(intervalId);
}, []);
```

## Solution: Use advanceTimersByTimeAsync()

**DO NOT use `vi.advanceTimersByTime()`** - it advances timers synchronously and can block microtasks.

**DO use `vi.advanceTimersByTimeAsync()`** - it advances timers and flushes Promise microtasks.

## Complete Test Pattern

**From:** `erkdesk/src/renderer/App.test.tsx`

```typescript
describe("auto-refresh", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("preserves selection by issue_number after refresh", async () => {
    const initialPlans = [
      makePlan({ issue_number: 10, title: "Alpha" }),
      makePlan({ issue_number: 20, title: "Beta" }),
    ];
    const refreshedPlans = [
      makePlan({ issue_number: 20, title: "Beta" }),
      makePlan({ issue_number: 10, title: "Alpha" }),
    ];

    vi.mocked(window.erkdesk.fetchPlans)
      .mockResolvedValueOnce({
        success: true,
        plans: initialPlans,
        count: 2,
      })
      .mockResolvedValueOnce({
        success: true,
        plans: refreshedPlans,
        count: 2,
      });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
    });

    const rowsBefore = screen.getAllByRole("row").slice(1);
    expect(rowsBefore[0]).toHaveClass("plan-list__row--selected");

    // Advance time by 15 seconds (REFRESH_INTERVAL_MS)
    await vi.advanceTimersByTimeAsync(15_000);

    await waitFor(() => {
      const rowsAfter = screen.getAllByRole("row").slice(1);
      expect(rowsAfter[1]).toHaveClass("plan-list__row--selected");
      expect(rowsAfter[0]).not.toHaveClass("plan-list__row--selected");
    });
  });
});
```

## Key Elements

### 1. Setup Fake Timers in beforeEach

```typescript
beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});
```

**Why `shouldAdvanceTime: true`:**

- Allows manual control of when timers fire
- Prevents real time from passing during tests
- Required for deterministic testing of intervals

### 2. Clean Up in afterEach

```typescript
afterEach(() => {
  vi.useRealTimers();
});
```

**Critical:** Fake timers persist across tests if not cleaned up. Always restore real timers in `afterEach()`.

### 3. Use advanceTimersByTimeAsync

```typescript
await vi.advanceTimersByTimeAsync(15_000);
```

**Why async:**

- Advances timers AND flushes Promise microtasks
- Allows `.then()` callbacks to execute
- Prevents test hangs with Promise-based code

**Alternative (synchronous):**

```typescript
vi.advanceTimersByTime(15_000); // WRONG for async code
```

This will NOT work correctly with Promises - callbacks won't fire.

### 4. Use waitFor After Advancing

```typescript
await vi.advanceTimersByTimeAsync(15_000);

await waitFor(() => {
  expect(screen.getByText("Beta")).toBeInTheDocument();
});
```

**Why waitFor:**

- Gives React time to re-render after state updates
- Retries assertions until they pass or timeout
- Handles asynchronous state updates gracefully

## Common Patterns

### Pattern: Test Interval Fires on Schedule

```typescript
it("refreshes every 15 seconds", async () => {
  const fetchMock = vi.mocked(window.erkdesk.fetchPlans);
  fetchMock.mockResolvedValue({ success: true, plans: [] });

  render(<App />);

  // Initial fetch
  expect(fetchMock).toHaveBeenCalledTimes(1);

  // Advance time, interval fires
  await vi.advanceTimersByTimeAsync(15_000);
  expect(fetchMock).toHaveBeenCalledTimes(2);

  // Advance again
  await vi.advanceTimersByTimeAsync(15_000);
  expect(fetchMock).toHaveBeenCalledTimes(3);
});
```

### Pattern: Test Silent Error Handling

**Scenario:** Errors during refresh shouldn't replace good data.

```typescript
it("errors during refresh don't replace data", async () => {
  const initialPlans = [makePlan({ issue_number: 1, title: "Keeper" })];

  vi.mocked(window.erkdesk.fetchPlans)
    .mockResolvedValueOnce({
      success: true,
      plans: initialPlans,
      count: 1,
    })
    .mockResolvedValueOnce({
      success: false,
      plans: [],
      count: 0,
      error: "Network error",
    });

  render(<App />);

  await waitFor(() => {
    expect(screen.getByText("Keeper")).toBeInTheDocument();
  });

  // Trigger refresh with error
  await vi.advanceTimersByTimeAsync(15_000);

  // Data should still be visible
  await waitFor(() => {
    expect(screen.getByText("Keeper")).toBeInTheDocument();
  });
  expect(screen.queryByText(/Error:/)).not.toBeInTheDocument();
});
```

## Alternative: shouldAdvanceTime Without Manual Advancement

If you want timers to advance automatically without manual control:

```typescript
beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: false });
});
```

**Use case:** Testing immediate timer setup without worrying about when timers fire.

**Tradeoff:** Less control over timing, harder to test specific sequences.

## Debugging Hangs

**Symptom:** Test hangs forever at `await vi.advanceTimersByTimeAsync()`

**Possible causes:**

1. **Forgot to mock async function**

   ```typescript
   // BAD: Forgot to mock fetchPlans
   render(<App />);
   await vi.advanceTimersByTimeAsync(15_000); // Hangs
   ```

   **Fix:** Mock all IPC calls:

   ```typescript
   vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({...});
   ```

2. **Interval cleanup not called**

   ```typescript
   // Component unmounts before interval is cleared
   const { unmount } = render(<App />);
   await vi.advanceTimersByTimeAsync(15_000);
   unmount(); // Too late - interval still running
   ```

   **Fix:** Ensure cleanup runs before advancing timers:

   ```typescript
   const { unmount } = render(<App />);
   unmount(); // Clean up first
   await vi.advanceTimersByTimeAsync(15_000); // Now safe
   ```

3. **Used advanceTimersByTime instead of advanceTimersByTimeAsync**

   ```typescript
   vi.advanceTimersByTime(15_000); // WRONG - blocks Promises
   ```

   **Fix:** Always use async variant with Promises:

   ```typescript
   await vi.advanceTimersByTimeAsync(15_000);
   ```

## Related Patterns

- [Erkdesk Auto-Refresh Patterns](../desktop-dash/erkdesk-auto-refresh-patterns.md) - The React pattern being tested
- [Selection Preservation by Value](../architecture/selection-preservation-by-value.md) - What we're testing with timer advancement

## Resources

- [Vitest Documentation: vi.useFakeTimers()](https://vitest.dev/api/vi.html#vi-usefaketimers)
- [Vitest Documentation: vi.advanceTimersByTimeAsync()](https://vitest.dev/api/vi.html#vi-advancetimersbytimedateasync)
