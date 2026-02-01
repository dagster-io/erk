---
title: Window Mock Patterns for Electron IPC Testing
category: testing
read_when:
  - testing erkdesk components that use window.erkdesk IPC bridge
  - encountering mock contamination between tests
  - tests passing individually but failing in CI
tripwires:
  - action: "testing components that use window.erkdesk IPC bridge"
    warning: "Mock window.erkdesk in setup.ts, but always call mockReset() in beforeEach before setting mockResolvedValue(). Forgetting this causes mock value contamination - tests pass individually but fail in CI."
  - action: "setting mock return values in test beforeEach"
    warning: "Order matters: call mockReset() FIRST (clears previous test's values), THEN mockResolvedValue(). Reverse order has no effect."
---

# Window Mock Patterns for Electron IPC Testing

Erkdesk components communicate with the Electron main process via the `window.erkdesk` IPC bridge. Testing these components requires global window mocks with careful reset discipline to prevent contamination between tests.

## The Problem

Tests that don't properly reset mocks exhibit a dangerous failure pattern:

- ✅ Tests pass when run individually (`pnpm test -- PlanList.test.tsx`)
- ❌ Tests fail when run sequentially in CI (mock values from test A persist into test B)

This is a **silent failure** - the test suite appears healthy during development but fails unpredictably in CI.

## The Root Cause

Vitest mocks are stateful. When you call `mockResolvedValue()` on a mock, that value persists until explicitly cleared. Without reset discipline:

```typescript
// Test A
beforeEach(() => {
  vi.mocked(window.erkdesk.invoke).mockResolvedValue({ plans: [planA] });
});

// Test B runs next in CI
beforeEach(() => {
  // BUG: planA is still in the mock! Test B sees planA instead of planB
  vi.mocked(window.erkdesk.invoke).mockResolvedValue({ plans: [planB] });
});
```

The second `mockResolvedValue()` call doesn't clear the first - it adds to the queue. Test B receives stale data.

## The Solution: mockReset() Discipline

**Always call `mockReset()` before setting test-specific mock values.**

### Pattern: Global Mock Setup

Define the mock once in `setup.ts`:

```typescript
// erkdesk/vitest-setup/setup.ts
import { vi } from "vitest";

declare global {
  interface Window {
    erkdesk: {
      invoke: (channel: string, ...args: unknown[]) => Promise<unknown>;
    };
  }
}

// Create global mock (runs once before all tests)
window.erkdesk = {
  invoke: vi.fn(),
};
```

### Pattern: Test-Specific Reset + Value

**Every test file** that uses `window.erkdesk.invoke` must follow this pattern:

```typescript
import { vi } from 'vitest'

describe('PlanList', () => {
  beforeEach(() => {
    // Step 1: RESET (clears previous test's values)
    vi.mocked(window.erkdesk.invoke).mockReset()

    // Step 2: SET (this test's values)
    vi.mocked(window.erkdesk.invoke).mockResolvedValue({
      plans: [/* test data */],
    })
  })

  it('renders plans', async () => {
    render(<PlanList />)
    await waitFor(() => {
      expect(screen.getByText('Plan Title')).toBeInTheDocument()
    })
  })
})
```

### ❌ Broken Pattern (No Reset)

```typescript
beforeEach(() => {
  // BUG: Missing mockReset() - previous test's values persist
  vi.mocked(window.erkdesk.invoke).mockResolvedValue({ plans: [planB] });
});
```

**Symptom**: Tests pass individually, fail in CI with unexpected data.

### ❌ Broken Pattern (Wrong Order)

```typescript
beforeEach(() => {
  // BUG: Reset AFTER setting value has no effect
  vi.mocked(window.erkdesk.invoke).mockResolvedValue({ plans: [planB] });
  vi.mocked(window.erkdesk.invoke).mockReset(); // Too late! Values already cleared
});
```

**Symptom**: Tests fail with "received undefined" errors.

## Order Matters

The correct sequence is:

1. **mockReset()** - clear previous test's mock configuration
2. **mockResolvedValue()** - set this test's return value

Reversing the order clears the value you just set.

## Why Not afterEach?

Resetting in `afterEach` is risky - if a test throws an error before `afterEach` runs, the mock remains contaminated. **Always reset in `beforeEach`** to guarantee clean state at the start of each test.

## Channel-Specific Mocking

If your component calls multiple IPC channels, use `mockImplementation` with a switch:

```typescript
beforeEach(() => {
  vi.mocked(window.erkdesk.invoke).mockReset();
  vi.mocked(window.erkdesk.invoke).mockImplementation(
    async (channel: string) => {
      switch (channel) {
        case "get-plans":
          return {
            plans: [
              /* data */
            ],
          };
        case "get-status":
          return { status: "ok" };
        default:
          throw new Error(`Unmocked channel: ${channel}`);
      }
    },
  );
});
```

The `default` case catches accidental calls to unmocked channels during test development.

## Verification Pattern

To assert that a component called the IPC bridge correctly:

```typescript
it('fetches plans on mount', async () => {
  render(<PlanList />)

  await waitFor(() => {
    expect(window.erkdesk.invoke).toHaveBeenCalledWith('get-plans')
  })
})
```

## Related

- [jsdom DOM API Stubs for Vitest](vitest-jsdom-stubs.md) - Stubbing missing DOM APIs
- [Erkdesk Component Testing Patterns](erkdesk-component-testing.md) - Async state testing with waitFor()
