---
title: Erkdesk Component Testing Patterns
category: testing
read_when:
  - writing tests for erkdesk React components
  - testing keyboard navigation in erkdesk
  - testing async state updates in React components
  - testing streaming action integration
  - mocking erkdesk IPC bridge in tests
---

# Erkdesk Component Testing Patterns

This document covers common testing patterns specific to erkdesk components, with examples from PlanList and SplitPane tests.

## Test File Structure

```typescript
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { PlanList } from "./PlanList";

describe("PlanList", () => {
  beforeEach(() => {
    // Reset mocks before each test
    vi.mocked(window.erkdesk.invoke).mockReset();
    vi.mocked(window.erkdesk.invoke).mockResolvedValue({
      plans: [
        /* test data */
      ],
    });
  });

  it("test description", async () => {
    // Test implementation
  });
});
```

**Key points:**

- Import from `@testing-library/react` (render, screen, waitFor)
- Import `userEvent` for keyboard/mouse interactions
- Reset `window.erkdesk.invoke` mock in `beforeEach`
- Use `async` functions for tests with `waitFor()` or user interactions

## Pattern: Async State Testing

React components fetch data in `useEffect`, which runs asynchronously after render. Assertions must wait for state updates.

### ❌ Broken: Immediate Assertion

```typescript
it('renders plans', () => {
  render(<PlanList />)
  // BUG: Component hasn't loaded data yet!
  expect(screen.getByText('Plan Title')).toBeInTheDocument() // Fails
})
```

### ✅ Correct: waitFor()

```typescript
it('renders plans', async () => {
  render(<PlanList />)

  // Wait for useEffect to complete and state to update
  await waitFor(() => {
    expect(screen.getByText('Plan Title')).toBeInTheDocument()
  })
})
```

**When to use `waitFor()`:**

- Component fetches data in `useEffect`
- Component updates state asynchronously
- Waiting for DOM changes after user interaction

**When NOT needed:**

- Component receives data via props (synchronous render)
- Testing static UI without state changes

## Pattern: Keyboard Navigation

Erkdesk uses keyboard shortcuts for navigation. Test with `userEvent.keyboard()`.

### Example: j/k Navigation

```typescript
it('navigates down with j key', async () => {
  const user = userEvent.setup()

  vi.mocked(window.erkdesk.invoke).mockResolvedValue({
    plans: [
      { id: '1', title: 'Plan 1' },
      { id: '2', title: 'Plan 2' },
    ],
  })

  render(<PlanList />)

  await waitFor(() => {
    expect(screen.getByText('Plan 1')).toBeInTheDocument()
  })

  // Press 'j' to move down
  await user.keyboard('j')

  // Verify selection moved to second item
  expect(screen.getByText('Plan 2')).toHaveClass('selected')
})
```

### Example: Arrow Key Navigation

```typescript
it('navigates with arrow keys', async () => {
  const user = userEvent.setup()
  render(<PlanList />)

  await waitFor(() => {
    expect(screen.getByText('Plan 1')).toBeInTheDocument()
  })

  await user.keyboard('{ArrowDown}')  // Special key syntax
  expect(screen.getByText('Plan 2')).toHaveClass('selected')

  await user.keyboard('{ArrowUp}')
  expect(screen.getByText('Plan 1')).toHaveClass('selected')
})
```

**userEvent keyboard syntax:**

- Regular keys: `'j'`, `'k'`, `'a'`
- Special keys: `'{ArrowDown}'`, `'{Enter}'`, `'{Escape}'`
- Modifiers: `'{Shift>}a{/Shift}'`, `'{Control>}c{/Control}'`

## Pattern: CSS Class Assertions

Erkdesk components use CSS classes for visual states (selected, focused, disabled).

```typescript
it('applies selected class to current item', async () => {
  render(<PlanList />)

  await waitFor(() => {
    expect(screen.getByText('Plan 1')).toHaveClass('selected')
  })
})

it('removes selected class from previous item', async () => {
  const user = userEvent.setup()
  render(<PlanList />)

  const plan1 = screen.getByText('Plan 1')
  const plan2 = screen.getByText('Plan 2')

  expect(plan1).toHaveClass('selected')
  expect(plan2).not.toHaveClass('selected')

  await user.keyboard('j')

  expect(plan1).not.toHaveClass('selected')
  expect(plan2).toHaveClass('selected')
})
```

**Matchers:**

- `.toHaveClass('selected')` - element has the class
- `.not.toHaveClass('selected')` - element doesn't have the class

## Pattern: Callback Verification

Components receive callbacks as props (e.g., `onSelect`, `onClick`). Verify they're called with correct arguments.

```typescript
it('calls onSelect when item clicked', async () => {
  const user = userEvent.setup()
  const onSelect = vi.fn()

  render(<PlanList onSelect={onSelect} />)

  await waitFor(() => {
    expect(screen.getByText('Plan 1')).toBeInTheDocument()
  })

  await user.click(screen.getByText('Plan 1'))

  expect(onSelect).toHaveBeenCalledWith('1')  // Called with plan ID
  expect(onSelect).toHaveBeenCalledTimes(1)   // Called exactly once
})
```

**Callback matchers:**

- `.toHaveBeenCalled()` - callback invoked at least once
- `.toHaveBeenCalledWith(arg1, arg2)` - callback received specific arguments
- `.toHaveBeenCalledTimes(n)` - callback invoked exactly n times

## Pattern: IPC Bridge Verification

Verify components call the Electron IPC bridge correctly.

```typescript
it('fetches plans on mount', async () => {
  render(<PlanList />)

  await waitFor(() => {
    expect(window.erkdesk.invoke).toHaveBeenCalledWith('get-plans')
  })
})

it('refreshes plans when refresh button clicked', async () => {
  const user = userEvent.setup()
  render(<PlanList />)

  // Wait for initial load
  await waitFor(() => {
    expect(window.erkdesk.invoke).toHaveBeenCalledTimes(1)
  })

  // Click refresh button
  await user.click(screen.getByRole('button', { name: 'Refresh' }))

  // Verify second call
  await waitFor(() => {
    expect(window.erkdesk.invoke).toHaveBeenCalledTimes(2)
  })
})
```

## Pattern: Test Data Setup

Create focused test data for each scenario. Don't share data between tests.

```typescript
describe('PlanList filtering', () => {
  it('shows open plans', async () => {
    vi.mocked(window.erkdesk.invoke).mockResolvedValue({
      plans: [
        { id: '1', title: 'Open Plan', status: 'open' },
      ],
    })

    render(<PlanList filter="open" />)

    await waitFor(() => {
      expect(screen.getByText('Open Plan')).toBeInTheDocument()
    })
  })

  it('shows closed plans', async () => {
    vi.mocked(window.erkdesk.invoke).mockResolvedValue({
      plans: [
        { id: '2', title: 'Closed Plan', status: 'closed' },
      ],
    })

    render(<PlanList filter="closed" />)

    await waitFor(() => {
      expect(screen.getByText('Closed Plan')).toBeInTheDocument()
    })
  })
})
```

Each test creates minimal data for its scenario. This makes tests:

- **Focused** - only relevant data present
- **Independent** - changing one test doesn't break others
- **Readable** - clear what data matters for the assertion

## Common Queries

### Finding Elements

```typescript
// By text content
screen.getByText("Plan Title");

// By role + accessible name
screen.getByRole("button", { name: "Submit" });
screen.getByRole("heading", { name: "Plans" });

// By test ID (use sparingly)
screen.getByTestId("plan-list");
```

**Prefer semantic queries:**

1. `getByRole()` - best for accessibility
2. `getByLabelText()` - for form inputs
3. `getByText()` - for text content
4. `getByTestId()` - last resort

### Query Variants

```typescript
// getBy* - throws if not found (use for assertions)
screen.getByText("Plan Title");

// queryBy* - returns null if not found (use for "should not exist")
expect(screen.queryByText("Plan Title")).not.toBeInTheDocument();

// findBy* - async, waits for element (use for async rendering)
await screen.findByText("Plan Title");
```

## Pattern: Streaming Action Testing

Components that manage streaming action state require special testing patterns to simulate real-time IPC events.

### Mocking Streaming APIs

Ensure `window.erkdesk` streaming methods are mocked in `vitest-setup/setup.ts`:

```typescript
global.window.erkdesk = {
  // ... other methods
  startStreamingAction: vi.fn(),
  onActionOutput: vi.fn(),
  onActionCompleted: vi.fn(),
  removeActionListeners: vi.fn(),
};
```

### Testing Streaming State Flow

To test components that manage streaming action state:

**Step 1: Capture callbacks from mocks**

```typescript
let outputCallback: ((event: ActionOutputEvent) => void) | null = null;
let completedCallback: ((event: ActionCompletedEvent) => void) | null = null;

beforeEach(() => {
  vi.mocked(window.erkdesk.onActionOutput).mockImplementation((cb) => {
    outputCallback = cb;
  });

  vi.mocked(window.erkdesk.onActionCompleted).mockImplementation((cb) => {
    completedCallback = cb;
  });
});
```

**Step 2: Trigger action and invoke callbacks**

```typescript
it('streams output in real-time', async () => {
  const user = userEvent.setup();
  render(<App />);

  // Trigger action start
  await user.click(screen.getByRole('button', { name: /submit/i }));

  // Simulate stdout event
  act(() => {
    outputCallback?.({ stream: "stdout", data: "Building project..." });
  });

  // Verify log appears
  expect(screen.getByText("Building project...")).toBeInTheDocument();

  // Simulate stderr event
  act(() => {
    outputCallback?.({ stream: "stderr", data: "Error: build failed" });
  });

  // Verify error styling
  expect(screen.getByText("Error: build failed")).toHaveClass("text-red-400");

  // Simulate completion
  act(() => {
    completedCallback?.({ success: false, error: "Build failed" });
  });

  // Verify status changed to error
  expect(screen.getByRole("heading")).toHaveClass("bg-red-500");
});
```

**Step 3: Verify cleanup**

```typescript
it('removes action listeners on unmount', () => {
  const { unmount } = render(<App />);

  unmount();

  expect(window.erkdesk.removeActionListeners).toHaveBeenCalled();
});
```

### LogPanel Test Coverage

When testing the LogPanel component:

```typescript
it('renders stdout logs with gray styling', () => {
  const logs = [{ stream: "stdout" as const, data: "Normal output" }];
  render(<LogPanel logs={logs} status="running" onDismiss={vi.fn()} />);

  const logLine = screen.getByText("Normal output");
  expect(logLine).toHaveClass("text-gray-300");
});

it('renders stderr logs with red styling', () => {
  const logs = [{ stream: "stderr" as const, data: "Error output" }];
  render(<LogPanel logs={logs} status="error" onDismiss={vi.fn()} />);

  const logLine = screen.getByText("Error output");
  expect(logLine).toHaveClass("text-red-400");
});

it.each([
  ["running", "bg-blue-500"],
  ["success", "bg-green-500"],
  ["error", "bg-red-500"],
])('displays %s status with %s background', (status, expectedClass) => {
  render(
    <LogPanel
      logs={[]}
      status={status as any}
      onDismiss={vi.fn()}
    />
  );

  const header = screen.getByRole("heading");
  expect(header).toHaveClass(expectedClass);
});

it('calls onDismiss when dismiss button clicked', async () => {
  const user = userEvent.setup();
  const onDismiss = vi.fn();
  render(<LogPanel logs={[]} status="success" onDismiss={onDismiss} />);

  const dismissButton = screen.getByRole("button", { name: /dismiss/i });
  await user.click(dismissButton);

  expect(onDismiss).toHaveBeenCalledTimes(1);
});
```

### Common Pitfalls

**Forgetting act() for async updates:**

When invoking callbacks that trigger state updates, wrap in `act()`:

```typescript
// WRONG: State update not wrapped
outputCallback?.({ stream: "stdout", data: "Test" });

// RIGHT: Wrapped in act()
act(() => {
  outputCallback?.({ stream: "stdout", data: "Test" });
});
```

**Note:** Some async updates may still trigger act() warnings in tests. This is expected behavior for complex streaming patterns and acceptable when tests pass.

**Not resetting mocks in beforeEach:**

Always reset mocks between tests. See [Window Mock Patterns](window-mock-patterns.md) for details on mock reset timing.

```typescript
beforeEach(() => {
  vi.mocked(window.erkdesk.onActionOutput).mockReset();
  vi.mocked(window.erkdesk.onActionCompleted).mockReset();
  vi.mocked(window.erkdesk.removeActionListeners).mockReset();
});
```

## Related

- [Window Mock Patterns](window-mock-patterns.md) - IPC bridge mocking discipline
- [Vitest Configuration](../desktop-dash/vitest-setup.md) - Test environment setup
- [jsdom DOM API Stubs](vitest-jsdom-stubs.md) - Required jsdom stubs
- [Erkdesk IPC Streaming Architecture](../architecture/erkdesk-ipc-streaming.md) - IPC event flow
- [Erkdesk Components](../desktop-dash/erkdesk-components.md) - LogPanel reference
