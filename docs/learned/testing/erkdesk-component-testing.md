---
title: Erkdesk Component Testing Patterns
category: testing
content_type: mixed
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

- [Window Mock Patterns](window-mock-patterns.md) - IPC bridge mocking discipline
- [Vitest Configuration](../desktop-dash/vitest-setup.md) - Test environment setup
- [jsdom DOM API Stubs](vitest-jsdom-stubs.md) - Required jsdom stubs
