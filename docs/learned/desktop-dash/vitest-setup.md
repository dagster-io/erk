---
title: Vitest Configuration for erkdesk
category: desktop-dash
read_when:
  - setting up test infrastructure for erkdesk
  - adding new tests to erkdesk
  - understanding erkdesk test environment
last_audited: "2026-02-05 20:38 PT"
audit_result: edited
---

# Vitest Configuration for erkdesk

This document covers the Vitest setup for erkdesk, the Electron desktop application in the erk monorepo.

## Why Vitest Over Jest?

Erkdesk uses Vite for building, making Vitest the natural choice for testing:

1. **Native Vite integration** - no additional build config (no Babel, no ts-jest)
2. **ESM support** - works with modern JavaScript modules out of the box
3. **Fast** - uses Vite's transformation pipeline, same as the build process
4. **Compatible API** - same API as Jest, easy migration path

## Configuration Files

### vitest.config.ts

See `erkdesk/vitest.config.ts` for the authoritative configuration. Key settings:

- **`globals: true`** - makes `describe`, `it`, `expect`, `vi` available without imports (matches Jest)
- **`environment: 'jsdom'`** - provides DOM APIs for React component rendering
- **`setupFiles: ["./src/test/setup.ts"]`** - runs before tests to stub missing jsdom APIs and create global mocks

### tsconfig.json

`erkdesk/tsconfig.json` includes `"types": ["vitest/globals"]` in `compilerOptions` to provide autocomplete and type checking for `describe`, `it`, `expect`, etc. without explicit imports.

### setup.ts

The setup file at `erkdesk/src/test/setup.ts` runs once before all tests. Its responsibilities:

1. Load jest-dom matchers (enables `expect(element).toBeInTheDocument()`)
2. Stub missing jsdom APIs (`scrollIntoView`, `ResizeObserver`) to prevent TypeError exceptions
3. Create a typed mock of `window.erkdesk` using the `ErkdeskAPI` interface from `erkdesk/src/types/erkdesk.d.ts`, providing mock implementations for all IPC bridge methods (`fetchPlans`, `executeAction`, `startStreamingAction`, etc.)

See [jsdom DOM API Stubs](../testing/vitest-jsdom-stubs.md) for details on stubbing, and [Window Mock Patterns](../testing/window-mock-patterns.md) for IPC mocking discipline.

## Running Tests

Run erkdesk tests locally or via Makefile:

- **Single run:** `pnpm test` (from erkdesk/) or `make erkdesk-test`
- **Watch mode:** `pnpm run test:watch` (from erkdesk/) or `make erkdesk-test-watch`

Note: Erkdesk tests are run separately from the Python test suite. The `make fast-ci` target does not include erkdesk tests.

See [Makefile Testing Targets](../cli/erkdesk-makefile-targets.md) for details on CI integration.

## Test File Conventions

### Colocation

Place test files next to source files:

```
erkdesk/src/renderer/components/
├── PlanList.tsx
├── PlanList.test.tsx      # Tests for PlanList
├── SplitPane.tsx
└── SplitPane.test.tsx     # Tests for SplitPane
```

**Why colocation?**

- Easy to find tests for a component
- Encourages writing tests when creating components
- Deleted components automatically delete their tests

### Naming

- Source: `ComponentName.tsx`
- Tests: `ComponentName.test.tsx`

## Test Dependencies

Test libraries are listed as devDependencies in `erkdesk/package.json`. The key packages are `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, and `@testing-library/user-event`.

## Common Patterns

See [Erkdesk Component Testing Patterns](../testing/erkdesk-component-testing.md) for rendering, async state updates, and user interaction examples.

## Related

- [jsdom DOM API Stubs](../testing/vitest-jsdom-stubs.md) - Required stubs for jsdom gaps
- [Window Mock Patterns](../testing/window-mock-patterns.md) - Electron IPC mocking discipline
- [Erkdesk Component Testing Patterns](../testing/erkdesk-component-testing.md) - Common test scenarios
- [Makefile Testing Targets](../cli/erkdesk-makefile-targets.md) - CI integration
