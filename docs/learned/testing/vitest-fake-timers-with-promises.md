---
title: Vitest Fake Timers with Promises
content_type: reference-cache
read_when:
  - "testing React components that use setInterval or setTimeout with async operations"
  - "debugging Vitest tests that hang when advancing fake timers"
  - "choosing between synchronous and async timer advancement in Vitest"
last_audited: "2026-02-08 13:55 PT"
audit_result: edited
category: testing
tripwires:
  - action: "using vi.advanceTimersByTime() in a test with Promise-based code"
    warning: "Use await vi.advanceTimersByTimeAsync() instead. The synchronous variant blocks Promise microtask flushing, causing hangs or silently skipped callbacks."
  - action: "using vi.useFakeTimers() without restoring in afterEach"
    warning: "Always call vi.useRealTimers() in afterEach(). Fake timers leak across tests and cause unpredictable failures in unrelated test suites."
---

# Vitest Fake Timers with Promises

## Why This Is Non-Obvious

Vitest's fake timer API has a subtle interaction with JavaScript's Promise microtask queue that causes tests to silently break. The root issue: `vi.advanceTimersByTime()` advances the clock synchronously without yielding to the microtask queue, so any `.then()` callbacks or `await` continuations scheduled by timer-triggered code never execute. The test appears to advance time, but Promise-based side effects (state updates, API call handlers) are permanently blocked.

This matters in erk because the erkdesk auto-refresh pattern uses `setInterval` that triggers `fetchPlans()` — a Promise-returning IPC call. The timer fires the interval callback, but the `.then()` that processes the response never runs under synchronous advancement.

## The Critical Decision: Sync vs Async Advancement

| Method                          | Microtask flushing                     | Use when                                                                       |
| ------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------ |
| `vi.advanceTimersByTime()`      | None — blocks microtask queue          | Timer callbacks are purely synchronous (no Promises, no `await`, no `.then()`) |
| `vi.advanceTimersByTimeAsync()` | Flushes microtasks between timer ticks | Timer callbacks trigger any async work (API calls, state updates, IPC)         |

**Default to the async variant.** The synchronous variant is only safe when you can guarantee the entire callback chain is synchronous — which is rare in React components. Using the wrong variant doesn't throw an error; it silently skips Promise continuations.

## Setup Requirements

Two configuration choices interact in non-obvious ways:

**`shouldAdvanceTime: true`** — This option is required when you want to manually control timer advancement with `advanceTimersByTimeAsync()`. Without it, fake timers auto-advance with real time, defeating the purpose of deterministic timer testing.

**`vi.useRealTimers()` in `afterEach`** — Fake timer state is global and leaks across tests. Forgetting cleanup causes cascading failures in unrelated tests that may not even use timers, making the root cause hard to trace.

<!-- Source: erkdesk/src/renderer/App.test.tsx, "auto-refresh" describe block -->

See the `auto-refresh` describe block in `erkdesk/src/renderer/App.test.tsx` for the canonical setup/teardown pattern using `beforeEach`/`afterEach`.

## Complete Test Composition Example

<!-- Third-party API composition: Vitest fake timers + React Testing Library -->
<!-- Shows how vi.useFakeTimers, mockResolvedValueOnce, advanceTimersByTimeAsync, and waitFor compose -->

The following test demonstrates how all the Vitest and React Testing Library APIs compose in a single realistic test. This is a third-party API composition example showing the interaction between `vi.useFakeTimers({ shouldAdvanceTime: true })`, `mockResolvedValueOnce` chaining, `vi.advanceTimersByTimeAsync()`, and `waitFor()`.

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

**What this shows:** The `beforeEach`/`afterEach` bracket fake timers. Two `mockResolvedValueOnce` calls chain to provide distinct responses for the initial fetch and the interval-triggered refresh. `advanceTimersByTimeAsync(15_000)` fires the interval and flushes the Promise from `fetchPlans()`. The final `waitFor` retries assertions until React re-renders with the refreshed data.

## Debugging Timer Test Hangs

When a test hangs at `await vi.advanceTimersByTimeAsync()`, three causes account for nearly all cases:

1. **Unmocked async function** — The interval fires and calls an IPC/API function that returns a real (never-resolving) Promise instead of a mock. Fix: ensure every async function called within the timer callback has a `mockResolvedValue` or `mockResolvedValueOnce`.

   ```typescript
   // WRONG: Forgot to mock fetchPlans — returns a never-resolving Promise
   render(<App />);
   await vi.advanceTimersByTimeAsync(15_000); // Hangs

   // CORRECT: Mock all IPC calls before rendering
   vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
     success: true,
     plans: [],
     count: 0,
   });
   render(<App />);
   await vi.advanceTimersByTimeAsync(15_000); // Resolves
   ```

2. **Synchronous advancement with async code** — Used `vi.advanceTimersByTime()` instead of the async variant. The Promise callbacks are permanently blocked. Fix: switch to `await vi.advanceTimersByTimeAsync()`.

   ```typescript
   // WRONG: Synchronous advancement blocks Promise microtasks
   vi.advanceTimersByTime(15_000);

   // CORRECT: Async advancement flushes microtask queue
   await vi.advanceTimersByTimeAsync(15_000);
   ```

3. **Component unmount timing** — The component unmounts (clearing the interval via cleanup) but the test tries to advance timers afterward, interacting with stale React state. Fix: advance timers while the component is still mounted, then unmount.

   ```typescript
   // WRONG: Unmount before advancing — interval already cleared
   const { unmount } = render(<App />);
   unmount();
   await vi.advanceTimersByTimeAsync(15_000);

   // CORRECT: Advance timers while component is mounted
   const { unmount } = render(<App />);
   await vi.advanceTimersByTimeAsync(15_000);
   unmount();
   ```

## Interaction with React Testing Library's waitFor

After advancing fake timers, React state updates from resolved Promises still need a render cycle to reflect in the DOM. The pattern is always: advance timers first, then `waitFor` the expected DOM state. This two-step sequence (timer advancement -> waitFor assertion) is required because `advanceTimersByTimeAsync` flushes microtasks but doesn't trigger React re-renders synchronously.

```typescript
// The two-step pattern: advance timers, then waitFor DOM assertions
await vi.advanceTimersByTimeAsync(15_000);

await waitFor(() => {
  expect(screen.getByText("Beta")).toBeInTheDocument();
});
```

<!-- Source: erkdesk/src/renderer/App.test.tsx, "preserves selection by issue_number after refresh" -->

See the `preserves selection by issue_number after refresh` test in `erkdesk/src/renderer/App.test.tsx` for this pattern in practice.

## Related Documentation

- [Erkdesk Auto-Refresh Patterns](../desktop-dash/erkdesk-auto-refresh-patterns.md) — The React interval pattern these tests exercise
- [Selection Preservation by Value](../architecture/selection-preservation-by-value.md) — Cross-data-refresh selection stability tested via timer advancement

## Sources

- [Vitest Documentation: vi.useFakeTimers()](https://vitest.dev/api/vi.html#vi-usefaketimers)
- [Vitest Documentation: vi.advanceTimersByTimeAsync()](https://vitest.dev/api/vi.html#vi-advancetimersbytimedateasync)
