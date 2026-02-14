---
title: Erkdesk Component Test Architecture
category: testing
third_party_references:
  - name: React Testing Library
    what: Query variants, query priority, findBy/getBy/queryBy semantics
  - name: Vitest
    what: vi.fn() matchers, vi.mocked() patterns
  - name: userEvent
    what: keyboard() syntax for regular keys, special keys, modifiers
read_when:
  - writing tests for erkdesk React components
  - deciding whether to test at component level or App level
  - adding keyboard navigation tests for erkdesk
  - creating test data factories for PlanRow
tripwires:
  - action: "testing keyboard navigation in a component test"
    warning: "Keyboard handlers (j/k) are registered on document in App, not on individual components. Test keyboard navigation in App.test.tsx, not component tests."
  - action: "testing IPC calls in a component test for a prop-driven component"
    warning: "PlanList and ActionToolbar receive data via props — they don't call window.erkdesk directly. IPC verification belongs in App.test.tsx where the actual fetch-state-props flow lives."
  - action: "creating inline PlanRow test data with all fields"
    warning: "Use the makePlan() factory with Partial<PlanRow> overrides. PlanRow has 18+ fields; inline objects go stale when the type changes. See any test file for the pattern."
last_audited: "2026-02-08 13:55 PT"
audit_result: clean
---

# Erkdesk Component Test Architecture

Erkdesk tests are split into two layers with distinct responsibilities. Understanding why the split exists prevents writing tests in the wrong place.

## The Two-Layer Split

<!-- Source: erkdesk/src/renderer/App.test.tsx -->
<!-- Source: erkdesk/src/renderer/components/PlanList.test.tsx -->
<!-- Source: erkdesk/src/renderer/components/ActionToolbar.test.tsx -->

| Layer               | Tests                                               | What it verifies                                                                                                   | Uses waitFor?                                        |
| ------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------- |
| **App integration** | `App.test.tsx`                                      | Async data flow: IPC fetch → state → child props. Keyboard navigation (j/k). Auto-refresh. Streaming. URL loading. | Yes — data arrives asynchronously via `fetchPlans()` |
| **Component unit**  | `PlanList.test.tsx`, `ActionToolbar.test.tsx`, etc. | Rendering from props. Click callbacks. CSS class application. Button enable/disable logic.                         | No — components receive data synchronously via props |

**Why this split matters**: PlanList is a controlled component — it receives `plans`, `selectedIndex`, and `onSelectIndex` as props. It has no `useEffect` that fetches data and no keyboard event listeners. Testing async data flow or keyboard navigation against PlanList directly would require mocking behavior that doesn't exist in that component. The App component owns the data-fetching `useEffect`, the keyboard `addEventListener`, and the IPC bridge calls, so those behaviors must be tested there.

**Anti-pattern**: Writing `await waitFor(...)` in a PlanList test. If you need `waitFor`, you're testing behavior that lives in App, not PlanList.

## The makePlan Factory Pattern

<!-- Source: erkdesk/src/renderer/components/PlanList.test.tsx, makePlan -->
<!-- Source: erkdesk/src/renderer/components/ActionToolbar.test.tsx, makePlan -->
<!-- Source: erkdesk/src/renderer/App.test.tsx, makePlan -->

`PlanRow` has 18+ fields. Every test file that needs plan data defines a local `makePlan(overrides: Partial<PlanRow>)` factory that provides sensible defaults and lets each test override only the fields relevant to its assertion.

This factory is duplicated in each test file rather than shared because:

- **Test files are self-contained** — no shared test utilities to maintain or import
- **Defaults differ by context** — `ActionToolbar.test.tsx` defaults `pr_number` to 42 and `exists_locally` to true (toolbar needs an actionable plan), while `PlanList.test.tsx` defaults to null/false (list just renders whatever it gets)
- **The `PlanRow` type enforces completeness** — when a field is added to `PlanRow` in `erkdesk.d.ts`, all `makePlan` factories fail to compile, forcing all test files to be updated

**Anti-pattern**: Creating a shared `makeTestPlan()` in a utils file. The per-file duplication is intentional — it keeps test defaults close to the tests that rely on them.

## IPC Mock Architecture

<!-- Source: erkdesk/src/test/setup.ts -->
<!-- Source: erkdesk/src/types/erkdesk.d.ts, ErkdeskAPI -->

The IPC mock has two layers that serve different purposes:

1. **Global mock** (`setup.ts`): Creates a `mockErkdesk` object typed to `ErkdeskAPI` with safe defaults (empty plans, successful results). This ensures components can render without crashing even if a test forgets to configure mocks.

2. **Per-test reset** (`beforeEach`): Each test file calls `mockReset()` on the specific methods it cares about, then sets test-specific return values.

The global mock is typed against the `ErkdeskAPI` interface, so adding a new IPC method to the interface forces the mock to be updated — compile-time enforcement that the mock stays in sync with the real API.

For mock reset discipline (order of operations, CI contamination pitfalls), see [Window Mock Patterns](window-mock-patterns.md).

## Auto-Refresh Testing

<!-- Source: erkdesk/src/renderer/App.test.tsx -->

Auto-refresh tests use `vi.useFakeTimers({ shouldAdvanceTime: true })` with `vi.advanceTimersByTimeAsync()` to simulate the refresh interval. Two cross-cutting insights:

- **Selection preservation**: After refresh, the selected plan is restored by `issue_number`, not by array index. Tests verify this by returning plans in a different order after the refresh timer fires.
- **Error resilience**: If a refresh fetch fails, the existing plan data is preserved (no error state shown). This is intentional — a transient network error shouldn't wipe the user's view.

For fake timer patterns and the `shouldAdvanceTime` requirement, see [Vitest Fake Timers with Promises](vitest-fake-timers-with-promises.md).

## Streaming Listener Lifecycle

<!-- Source: erkdesk/src/renderer/App.test.tsx -->

App registers `onActionOutput` and `onActionCompleted` listeners on mount and calls `removeActionListeners` on unmount. Tests verify both sides of this lifecycle by checking that listeners are registered after render and cleaned up after `unmount()`. This prevents memory leaks and stale callbacks when the component is re-mounted.

## React Testing Library Quick Reference

<!-- Source: React Testing Library docs -->
<!-- Source: Vitest docs -->

### Query Variants

| Variant    | No Match       | 1 Match         | 1+ Match | Await? | Use When                         |
| ---------- | -------------- | --------------- | -------- | ------ | -------------------------------- |
| `getBy*`   | throws         | returns element | throws   | No     | Asserting element exists         |
| `queryBy*` | returns `null` | returns element | throws   | No     | Asserting element does NOT exist |
| `findBy*`  | throws         | returns element | throws   | Yes    | Waiting for async rendering      |

```typescript
// getBy* - throws if not found (use for positive assertions)
screen.getByText("Plan Title");

// queryBy* - returns null if not found (use for negative assertions)
expect(screen.queryByText("Plan Title")).not.toBeInTheDocument();

// findBy* - async, waits for element (use for async rendering)
await screen.findByText("Plan Title");
```

### Query Priority

Prefer queries in this order (most semantic to least):

1. **`getByRole()`** — best for accessibility, matches ARIA roles (`button`, `heading`, `list`, etc.)
2. **`getByLabelText()`** — for form inputs associated with a `<label>`
3. **`getByText()`** — for visible text content
4. **`getByTestId()`** — last resort when no semantic query applies

```typescript
// By role + accessible name (preferred)
screen.getByRole("button", { name: "Submit" });
screen.getByRole("heading", { name: "Plans" });

// By text content
screen.getByText("Plan Title");

// By test ID (use sparingly)
screen.getByTestId("plan-list");
```

### `userEvent.keyboard()` Syntax

| Input         | Syntax                    | Example                                    |
| ------------- | ------------------------- | ------------------------------------------ |
| Regular key   | `'j'`                     | `await user.keyboard('j')`                 |
| Special key   | `'{KeyName}'`             | `await user.keyboard('{ArrowDown}')`       |
| Multiple keys | concatenate               | `await user.keyboard('jjk')`               |
| Modifier hold | `'{Mod>}key{/Mod}'`       | `await user.keyboard('{Shift>}a{/Shift}')` |
| Enter/Escape  | `'{Enter}'`, `'{Escape}'` | `await user.keyboard('{Enter}')`           |

Always call `userEvent.setup()` before using keyboard:

```typescript
const user = userEvent.setup();
await user.keyboard("j");
```

### Async State Testing with `waitFor()`

Components that fetch data in `useEffect` update state asynchronously after render. Assertions must wait:

```typescript
// WRONG: Immediate assertion fails — useEffect hasn't completed
render(<App />);
expect(screen.getByText("Plan Title")).toBeInTheDocument(); // Fails

// CORRECT: waitFor retries until assertion passes
render(<App />);
await waitFor(() => {
  expect(screen.getByText("Plan Title")).toBeInTheDocument();
});
```

**When to use `waitFor()`**: Component fetches data in `useEffect`, updates state asynchronously, or DOM changes after user interaction.

**When NOT needed**: Component receives data via props (synchronous render), testing static UI without state changes.

### CSS Class Assertions

```typescript
// Element has the class
expect(screen.getByText("Plan 1")).toHaveClass("selected");

// Element does not have the class
expect(screen.getByText("Plan 2")).not.toHaveClass("selected");
```

### Callback Verification

```typescript
const onSelect = vi.fn();

render(<PlanList onSelect={onSelect} />);
await user.click(screen.getByText("Plan 1"));

// Verify callback was invoked
expect(onSelect).toHaveBeenCalled();
expect(onSelect).toHaveBeenCalledWith("1");     // specific arguments
expect(onSelect).toHaveBeenCalledTimes(1);       // exact call count
```

## Related

- [Window Mock Patterns](window-mock-patterns.md) — IPC mock reset discipline and CI contamination prevention
- [Vitest Configuration](../desktop-dash/vitest-setup.md) — Three-file coordination (vitest.config.ts, tsconfig.json, setup.ts)
- [jsdom DOM API Stubs](vitest-jsdom-stubs.md) — scrollIntoView, ResizeObserver, and other missing jsdom APIs
- [Vitest Fake Timers with Promises](vitest-fake-timers-with-promises.md) — shouldAdvanceTime and async timer patterns
