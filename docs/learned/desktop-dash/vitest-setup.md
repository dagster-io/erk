---
title: Vitest Configuration for erkdesk
category: desktop-dash
read_when:
  - setting up test infrastructure for erkdesk
  - adding new tests to erkdesk
  - understanding erkdesk test environment
---

# Vitest Configuration for erkdesk

This document covers the complete Vitest setup for erkdesk, the Electron desktop application in the erk monorepo.

## Why Vitest Over Jest?

Erkdesk uses Vite for building, making Vitest the natural choice for testing:

1. **Native Vite integration** - no additional build config (no Babel, no ts-jest)
2. **ESM support** - works with modern JavaScript modules out of the box
3. **Fast** - uses Vite's transformation pipeline, same as the build process
4. **Compatible API** - same API as Jest, easy migration path

## Configuration Files

### vitest.config.ts

```typescript
import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true, // Enable describe/it/expect without imports
    environment: "jsdom", // Browser-like DOM for React components
    setupFiles: ["./vitest-setup/setup.ts"], // Load stubs and mocks
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"), // Support @ imports
    },
  },
});
```

Key settings:

- **`globals: true`** - makes `describe`, `it`, `expect`, `vi` available without imports (matches Jest)
- **`environment: 'jsdom'`** - provides DOM APIs for React component rendering
- **`setupFiles`** - runs before tests to stub missing jsdom APIs and create global mocks

### tsconfig.json

Enable TypeScript types for Vitest globals:

```json
{
  "compilerOptions": {
    "types": ["vitest/globals"]
  }
}
```

This provides autocomplete and type checking for `describe`, `it`, `expect`, etc. without explicit imports.

### setup.ts

The setup file runs once before all tests to prepare the environment:

```typescript
// erkdesk/vitest-setup/setup.ts
import "@testing-library/jest-dom"; // Enables toBeInTheDocument() matchers
import { vi } from "vitest";

// Stub missing jsdom APIs
Element.prototype.scrollIntoView = vi.fn();

// Mock Electron IPC bridge
declare global {
  interface Window {
    erkdesk: {
      invoke: (channel: string, ...args: unknown[]) => Promise<unknown>;
    };
  }
}

window.erkdesk = {
  invoke: vi.fn(),
};
```

**Setup responsibilities:**

1. Load jest-dom matchers (enables `expect(element).toBeInTheDocument()`)
2. Stub missing jsdom APIs to prevent TypeError exceptions
3. Create global mocks for Electron-specific APIs

See [jsdom DOM API Stubs](../testing/vitest-jsdom-stubs.md) for details on stubbing, and [Window Mock Patterns](../testing/window-mock-patterns.md) for IPC mocking discipline.

## Running Tests

### Local Development

```bash
# Single run (CI mode)
pnpm test

# Watch mode (re-runs on file changes)
pnpm run test:watch
```

### Via Makefile

```bash
# Single run (CI mode)
make erkdesk-test

# Watch mode
make erkdesk-test-watch
```

The Makefile targets wrap `pnpm` commands for consistency with other erk testing patterns.

### In CI

```bash
# Fast CI includes erkdesk tests alongside Python unit tests
make fast-ci

# Total tests: 4712+ (Python unit tests + erkdesk component tests)
```

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

These are devDependencies in `erkdesk/package.json`:

| Package                       | Version | Purpose                                       |
| ----------------------------- | ------- | --------------------------------------------- |
| `vitest`                      | ^4.0.18 | Test runner and assertion library             |
| `jsdom`                       | ^27.4.0 | DOM implementation for Node.js                |
| `@testing-library/react`      | ^16.3.2 | React component testing utilities             |
| `@testing-library/jest-dom`   | ^6.9.1  | Custom matchers (toBeInTheDocument, etc.)     |
| `@testing-library/user-event` | ^14.6.1 | User interaction simulation (keyboard, mouse) |

## Common Patterns

### Rendering Components

```typescript
import { render, screen } from '@testing-library/react'

it('renders component', () => {
  render(<MyComponent />)
  expect(screen.getByText('Hello')).toBeInTheDocument()
})
```

### Async State Updates

React state updates happen asynchronously. Use `waitFor()` to wait for changes:

```typescript
import { render, screen, waitFor } from '@testing-library/react'

it('loads data on mount', async () => {
  render(<PlanList />)

  // Wait for useEffect to complete
  await waitFor(() => {
    expect(screen.getByText('Plan Title')).toBeInTheDocument()
  })
})
```

See [Erkdesk Component Testing Patterns](../testing/erkdesk-component-testing.md) for more examples.

### User Interactions

```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

it('handles keyboard navigation', async () => {
  const user = userEvent.setup()
  render(<PlanList />)

  await user.keyboard('j')  // Press 'j' key
  expect(screen.getByText('Plan 2')).toHaveClass('selected')
})
```

## Related

- [jsdom DOM API Stubs](../testing/vitest-jsdom-stubs.md) - Required stubs for jsdom gaps
- [Window Mock Patterns](../testing/window-mock-patterns.md) - Electron IPC mocking discipline
- [Erkdesk Component Testing Patterns](../testing/erkdesk-component-testing.md) - Common test scenarios
- [Makefile Testing Targets](../cli/erkdesk-makefile-targets.md) - CI integration
