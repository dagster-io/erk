---
title: Vitest Mock Reset Discipline for Shared Global Mocks
category: testing
read_when:
  - testing erkdesk components that use window.erkdesk IPC bridge
  - encountering mock contamination between tests
  - tests passing individually but failing in CI
  - writing beforeEach blocks that configure Vitest mocks
tripwires:
  - action: "setting mock return values in test beforeEach without calling mockReset() first"
    warning: "Always call mockReset() BEFORE mockResolvedValue(). Without reset, previous test's mock values persist — causing tests to pass individually but fail in CI due to cross-test contamination."
  - action: "resetting mocks in afterEach instead of beforeEach"
    warning: "Use beforeEach for mock resets, not afterEach. If a test throws before afterEach runs, the mock remains contaminated for the next test."
---

# Vitest Mock Reset Discipline for Shared Global Mocks

## The CI Contamination Problem

When a global mock (like `window.erkdesk` in erkdesk's test setup) is shared across tests, Vitest mock state leaks between tests unless explicitly cleared. This produces a dangerous failure mode:

- Tests pass when run individually during development
- Tests fail when run sequentially in CI because mock values from test A persist into test B

This is especially insidious because the developer never sees the failure locally — it only manifests in CI where test execution order differs.

## Why This Happens

Vitest's `mockResolvedValue()` is additive, not replacing. Calling it a second time doesn't clear the previous value — it queues a new one. Without an explicit `mockReset()`, mock state accumulates across tests in the same file and across files sharing a global mock.

## The Two-Step Reset Pattern

<!-- Source: erkdesk/src/renderer/App.test.tsx -->

Every `beforeEach` that configures a shared mock must follow a strict two-step sequence:

1. **`mockReset()`** — clears all previous mock configuration (return values, implementations, call history)
2. **`mockResolvedValue()` / `mockImplementation()`** — sets this test's specific behavior

See the `beforeEach` block in `App.test.tsx` for the canonical example — it resets every `window.erkdesk` method individually before each test.

### Anti-Patterns

**WRONG: Missing reset**

```typescript
// BUG: Previous test's mockResolvedValue still queued
beforeEach(() => {
  vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
    success: true,
    plans: [],
  });
});
```

Symptom: Tests pass alone, fail in CI with unexpected data from a previous test.

**WRONG: Reset after set**

```typescript
// BUG: mockReset() wipes the value you just configured
beforeEach(() => {
  vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
    success: true,
    plans: [],
  });
  vi.mocked(window.erkdesk.fetchPlans).mockReset(); // Oops — now returns undefined
});
```

Symptom: Tests fail with undefined/null errors.

## Why beforeEach, Not afterEach

Resetting in `afterEach` is fragile: if a test throws an unhandled error, `afterEach` may not run (depending on the test runner configuration), leaving the mock contaminated for the next test. Resetting in `beforeEach` guarantees clean state regardless of how the previous test exited.

## The Two-Layer Mock Architecture

<!-- Source: erkdesk/src/test/setup.ts -->
<!-- Source: erkdesk/src/types/erkdesk.d.ts, ErkdeskAPI -->

erkdesk's IPC mocks operate at two layers:

| Layer                  | Purpose                                                    | Where                          | Staleness protection                                                |
| ---------------------- | ---------------------------------------------------------- | ------------------------------ | ------------------------------------------------------------------- |
| **Global defaults**    | Safe fallback values so components render without crashing | `setup.ts`                     | Typed against `ErkdeskAPI` — adding a new method forces mock update |
| **Per-test overrides** | Scenario-specific return values                            | `beforeEach` in each test file | `mockReset()` clears the previous test's configuration first        |

The global mock in `setup.ts` is typed against the `ErkdeskAPI` interface, so the TypeScript compiler enforces that the mock stays in sync with the real IPC bridge — a new method on the interface produces a compile error until the mock is updated.

The key insight: global defaults exist to prevent crashes when a test doesn't configure a specific method. Per-test `mockReset()` + `mockResolvedValue()` overrides the defaults with scenario-specific behavior. Without the reset step, you get the previous test's overrides instead of the global defaults.

## When to Reset Specific Methods vs All Methods

<!-- Source: erkdesk/src/renderer/App.test.tsx -->
<!-- Source: erkdesk/src/renderer/components/SplitPane.test.tsx -->

`App.test.tsx` resets every `window.erkdesk` method because App calls most of them. `SplitPane.test.tsx` resets only `updateWebViewBounds` because that's the only method SplitPane uses directly. The principle: reset every method your test's component calls, no more. Resetting methods your component doesn't use adds noise without preventing bugs.

## Related

- [Erkdesk Component Test Architecture](erkdesk-component-testing.md) — two-layer test split (App integration vs component unit) and IPC mock architecture overview
- [jsdom DOM API Stubs for Vitest](vitest-jsdom-stubs.md) — the environment stub layer (scrollIntoView, ResizeObserver) that complements the behavior mock layer
