---
title: jsdom DOM API Stubs for Vitest
category: testing
read_when:
  - writing React component tests with Vitest + jsdom
  - encountering "scrollIntoView is not a function" errors
  - setting up Vitest test environment
  - mocking ResizeObserver or IntersectionObserver in jsdom tests
tripwires:
  - action: "writing React component tests with Vitest + jsdom"
    warning: "jsdom doesn't implement Element.prototype.scrollIntoView(). Stub in setup.ts with `Element.prototype.scrollIntoView = vi.fn()` before tests run to avoid TypeError."
  - action: "mocking ResizeObserver or IntersectionObserver in jsdom tests"
    warning: "Use class syntax: `class ResizeObserver { observe = vi.fn(); ... }`. Do NOT use `vi.fn().mockImplementation()` - it returns a function, not a constructable class, causing 'ResizeObserver is not a constructor' TypeError."
---

# jsdom DOM API Stubs for Vitest

When testing React components with Vitest + jsdom, jsdom lacks several browser APIs that components commonly use. Attempting to use these missing APIs results in TypeErrors at runtime.

## The Problem

jsdom is a pure JavaScript DOM implementation that doesn't include all browser APIs. Components that call these APIs during tests will throw errors:

```
TypeError: element.scrollIntoView is not a function
```

This is particularly common with:

- `Element.prototype.scrollIntoView()` - used for keyboard navigation, focus management
- `Element.prototype.getBoundingClientRect()` - partially implemented (returns zeros)
- `window.matchMedia()` - media query matching
- `ResizeObserver` - element resize detection

## The Solution

Stub missing APIs in `setup.ts` before any component tests run. Vitest executes setup files before importing test files, ensuring stubs are in place when components render.

### Example: scrollIntoView Stub

```typescript
// erkdesk/vitest-setup/setup.ts
import { vi } from "vitest";

// Stub missing jsdom APIs
Element.prototype.scrollIntoView = vi.fn();
```

### Other Common Stubs

```typescript
// Partial getBoundingClientRect (jsdom returns all zeros)
Element.prototype.getBoundingClientRect = vi.fn(() => ({
  width: 100,
  height: 100,
  top: 0,
  left: 0,
  bottom: 100,
  right: 100,
  x: 0,
  y: 0,
  toJSON: () => {},
}));

// matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// ResizeObserver - MUST use class syntax, not vi.fn().mockImplementation()
class ResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
global.ResizeObserver = ResizeObserver;
```

## ResizeObserver: Why Class Syntax is Required

When mocking `ResizeObserver` or `IntersectionObserver`, you **must use class syntax**, not `vi.fn().mockImplementation()`.

**WRONG:**

```typescript
// Returns a function, not a constructable class
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));
```

This fails with `TypeError: ResizeObserver is not a constructor` because `vi.fn()` returns a function, but `new ResizeObserver()` requires a class constructor.

**CORRECT:**

```typescript
// Proper class constructor
class ResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
global.ResizeObserver = ResizeObserver;
```

The class syntax creates a true constructor function that can be instantiated with `new`.

This pattern applies to any browser API instantiated with `new`: `ResizeObserver`, `IntersectionObserver`, `MutationObserver`, etc.

## When to Add Stubs

**Add stubs reactively**, not proactively. When a test fails with "X is not a function", add the stub to `setup.ts`. Don't guess which APIs might be needed - let test failures guide you.

## Configuration

Ensure Vitest loads the setup file:

```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest-setup/setup.ts"], // Load stubs before tests
  },
});
```

## Why Not Mock in Individual Tests?

Global stubs belong in `setup.ts` because:

1. **Single source of truth** - one place to maintain stubs
2. **Runs before imports** - stubs available when components first render
3. **Prevents duplication** - every test file would need the same setup

Individual test files should only mock **behavior-specific** values (like IPC responses), not **environment-level** APIs.

## Related

- [Window Mock Patterns for Electron IPC Testing](window-mock-patterns.md) - Mocking `window.erkdesk` for IPC
- [Vitest Configuration for erkdesk](../desktop-dash/vitest-setup.md) - Complete Vitest setup
