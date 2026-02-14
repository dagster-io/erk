---
title: jsdom DOM API Stubs for Vitest
category: testing
content_type: third_party_reference
last_audited: "2026-02-08 13:55 PT"
audit_result: edited
read_when:
  - writing React component tests with Vitest + jsdom
  - encountering "X is not a function" errors in jsdom test runs
  - adding a new browser API stub to the test setup
tripwires:
  - action: "writing React component tests with Vitest + jsdom"
    warning: "jsdom doesn't implement several browser APIs (scrollIntoView, ResizeObserver). Check erkdesk/src/test/setup.ts for existing stubs before adding new ones."
  - action: "mocking a browser API in an individual test file"
    warning: "Environment-level API stubs belong in setup.ts (runs before all tests), not in individual test files. Only mock behavior-specific values (like IPC responses) per-test."
---

# jsdom DOM API Stubs for Vitest

## Why Stubs Are Needed

jsdom is a pure JavaScript DOM implementation that intentionally omits layout-related and visual browser APIs. Components that call these APIs during tests throw `TypeError: X is not a function`. This is a jsdom design decision, not a bug — jsdom doesn't perform layout, so scroll/resize APIs have no meaningful implementation.

## The Two-Layer Mock Architecture

erkdesk's test setup separates concerns into two layers, and confusing them is the most common mistake:

| Layer                 | What it stubs                                             | Where it lives                           | Why                                           |
| --------------------- | --------------------------------------------------------- | ---------------------------------------- | --------------------------------------------- |
| **Environment stubs** | Missing browser APIs (`scrollIntoView`, `ResizeObserver`) | `setup.ts` (runs before all tests)       | jsdom gaps — every component needs these      |
| **Behavior mocks**    | App-specific interfaces (`window.erkdesk` IPC)            | `setup.ts` defaults + per-test overrides | Test-specific return values vary per scenario |

The key insight: environment stubs are **no-op shims** that prevent crashes, while behavior mocks are **configurable fakes** that drive test scenarios. Both live in setup.ts for the defaults, but only behavior mocks should be overridden in individual tests.

<!-- Source: erkdesk/src/test/setup.ts -->

See `erkdesk/src/test/setup.ts` for all current stubs and the default `window.erkdesk` mock.

## jsdom Missing API Stubs

These are the stub implementations for browser APIs that jsdom does not provide. All stubs live in `setup.ts` and run before any test files are imported.

### Element.prototype.scrollIntoView

jsdom has no layout engine, so `scrollIntoView` is undefined. A simple `vi.fn()` no-op assigned to `Element.prototype.scrollIntoView` prevents `TypeError` crashes.

### ResizeObserver

jsdom does not implement `ResizeObserver`. The stub uses a class with `observe`, `unobserve`, and `disconnect` as `vi.fn()` no-ops assigned to `global.ResizeObserver`.

Both stubs are defined in `erkdesk/src/test/setup.ts`. If a new jsdom gap surfaces, add the stub there following the same no-op pattern.

## When to Add a New Stub

**Add stubs reactively, not proactively.** When a test fails with `TypeError: element.X is not a function`, that's the signal to add a stub to setup.ts. Don't preemptively stub APIs that no component uses — it obscures which APIs the codebase actually depends on.

The current stubs (`scrollIntoView`, `ResizeObserver`) were each added in response to a specific component needing them:

- `scrollIntoView` — used by `PlanList.tsx` for keyboard navigation
- `ResizeObserver` — used by `SplitPane.tsx` for resize detection

## Configuration

<!-- Source: erkdesk/vitest.config.ts -->

The setup file path is configured in `erkdesk/vitest.config.ts` via the `setupFiles` array (currently `./src/test/setup.ts`). Vitest executes setup files before importing any test files, which is why environment stubs must live there — they need to be in place before components first render.

## Anti-Patterns

**WRONG: Stubbing a browser API in every test file that needs it**

This leads to duplication and ordering bugs. If a component renders during import (e.g., module-level side effects), the stub won't be ready. Setup.ts runs before all imports.

**WRONG: Adding return values to environment stubs**

Environment stubs should be no-ops (`vi.fn()`), not realistic implementations. If a test needs `getBoundingClientRect` to return specific dimensions, that's a behavior mock and belongs in the individual test, not in setup.ts where it affects every test.

## Related

- [Window Mock Patterns for Electron IPC Testing](window-mock-patterns.md) — the behavior mock layer for `window.erkdesk`
- [Vitest Configuration for erkdesk](../desktop-dash/vitest-setup.md) — complete Vitest setup including environment and plugins
