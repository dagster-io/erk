---
title: erkdesk App Component Architecture
read_when:
  - "modifying the erkdesk App component"
  - "understanding erkdesk state management"
  - "implementing new features in the erkdesk dashboard"
tripwires:
  - action: "storing derived state in useState"
    warning: "App.tsx follows state lifting: only store plan data, selectedIndex, loading, error, and log state. Derived values like selectedPlan are computed inline."
  - action: "breaking the auto-refresh selection preservation logic"
    warning: "Auto-refresh preserves selection by issue_number, not by array index. Always use issue_number to find the new index after refresh."
---

# erkdesk App Component Architecture

The `App.tsx` component is the root of the erkdesk Electron renderer. It owns all application state and lifts it to child components following a controlled component pattern.

## State Ownership

App.tsx owns 7 pieces of state:

### Core Plan State

| State           | Type        | Purpose                                            |
| --------------- | ----------- | -------------------------------------------------- | --------------------------------- |
| `plans`         | `PlanRow[]` | Full list of erk plans from `erk dash-data --json` |
| `selectedIndex` | `number`    | Currently selected row index (-1 if none)          |
| `loading`       | `boolean`   | Initial fetch in progress                          |
| `error`         | `string     | null`                                              | Error message from fetch failures |

### Log Panel State

| State             | Type        | Purpose                 |
| ----------------- | ----------- | ----------------------- | -------------------------------- | ---------------------- |
| `logLines`        | `LogLine[]` | Streaming action output |
| `logStatus`       | `"running"  | "success"               | "error"`                         | Final status of action |
| `logVisible`      | `boolean`   | Log panel visibility    |
| `runningActionId` | `string     | null`                   | ID of currently executing action |

**Ref state**: `lastLoadedUrlRef` tracks the last URL loaded in WebView to prevent redundant loads.

## State Lifting Pattern

App.tsx passes state down to controlled components:

```tsx
<PlanList
  plans={plans}
  selectedIndex={selectedIndex}
  onSelectIndex={setSelectedIndex}
  loading={loading}
  error={error}
/>

<ActionToolbar
  selectedPlan={selectedPlan}
  runningActionId={runningActionId}
  onActionStart={handleActionStart}
/>

<LogPanel
  lines={logLines}
  status={logStatus}
  visible={logVisible}
  onDismiss={handleLogDismiss}
/>
```

**Key insight**: Child components are stateless and controlled. They receive props and call callbacks to mutate parent state.

## Auto-Refresh with Selection Preservation

Every 15 seconds (`REFRESH_INTERVAL_MS`), App.tsx re-fetches plan data and preserves selection by `issue_number`:

> **Source**: See [`App.tsx:42-61`](../../../erkdesk/src/renderer/App.tsx)

The effect sets up a `setInterval` that fetches plans every `REFRESH_INTERVAL_MS` (15s). On each refresh, it preserves selection by finding the previously-selected `issue_number` in the new plan array, falling back to index 0 if the plan is gone.

**Why this works**:

- Plans can be reordered (e.g., by PR state changes)
- Issue number is stable across refreshes
- Falls back to index 0 if previously selected plan is gone

**Tripwire**: Don't preserve selection by index — the selected plan might move to a different index after refresh.

## Keyboard Navigation

App.tsx implements j/k and arrow key navigation:

> **Source**: See [`App.tsx:63-81`](../../../erkdesk/src/renderer/App.tsx)

A `useCallback` handler listens for `j`/`ArrowDown` (increment) and `k`/`ArrowUp` (decrement) keys, clamping with `Math.min`/`Math.max` to prevent out-of-range indices. A `useEffect` registers and cleans up the `keydown` listener.

**Pattern**: Bounds checking with `Math.min` and `Math.max` prevents out-of-range indices.

## URL Loading Strategy

When selection changes, App.tsx loads the corresponding URL in the WebView:

> **Source**: See [`App.tsx:83-91`](../../../erkdesk/src/renderer/App.tsx)

The effect bounds-checks `selectedIndex`, resolves the URL (`pr_url` preferred over `issue_url`), and loads it via IPC only if the URL has changed (deduplication via `lastLoadedUrlRef`).

**Priority**: `pr_url` is preferred over `issue_url` (PRs are more actionable than issues).

**Deduplication**: `lastLoadedUrlRef` prevents redundant IPC calls when URL hasn't changed.

## Streaming Action Execution

App.tsx coordinates streaming actions through IPC event listeners:

> **Source**: See [`App.tsx:93-127`](../../../erkdesk/src/renderer/App.tsx)

`handleActionStart` resets log state, shows the log panel, sets the running action ID, and starts streaming via IPC. A separate `useEffect` registers `onActionOutput` (appends to `logLines`) and `onActionCompleted` (updates status, clears running action) listeners, with cleanup via `removeActionListeners()`.

**Pattern**: Event listeners are registered once on mount and cleaned up on unmount.

**State updates**: Action output appends to `logLines`, completion updates `logStatus` and clears `runningActionId`.

## Component Hierarchy

```
App
├── ActionToolbar (controlled)
│   └── Actions buttons with availability predicates
├── SplitPane
│   └── PlanList (controlled)
│       └── List of plans with selection
└── LogPanel (controlled)
    └── Streaming output drawer
```

## Related Documentation

- [Action Toolbar](action-toolbar.md) — Action availability predicates and styling
- [IPC Actions](ipc-actions.md) — IPC handler pattern and event flow
- [erkdesk Tripwires](tripwires.md) — Critical patterns to follow
