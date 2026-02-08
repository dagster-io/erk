---
title: erkdesk App Architecture
read_when:
  - "modifying App.tsx state or effects"
  - "understanding the WebView overlay approach"
  - "adding new state or auto-refresh behavior to erkdesk"
tripwires:
  - action: "storing derived state in useState"
    warning: "selectedPlan is computed inline from plans[selectedIndex], not stored in state. Never cache derived values — compute them on render."
  - action: "preserving selection by array index across refresh"
    warning: "Auto-refresh reorders plans. Selection must be preserved by issue_number, not by index. See the setInterval effect in App.tsx."
  - action: "loading URLs without deduplication"
    warning: "lastLoadedUrlRef prevents redundant IPC calls. Always check if the URL actually changed before calling loadWebViewURL."
  - action: "adding state to child components"
    warning: "PlanList, ActionToolbar, and LogPanel are fully controlled (stateless). All state lives in App.tsx. Pass props down, callbacks up."
---

# erkdesk App Architecture

## Why the State Lives in App.tsx

erkdesk follows a strict state-lifting pattern: App.tsx owns all application state, and child components (PlanList, ActionToolbar, LogPanel) are fully controlled. This isn't just React convention — it's required by two cross-cutting concerns:

1. **Auto-refresh must coordinate selection and plan data atomically.** If PlanList owned its own selection state, the refresh effect in App.tsx couldn't safely remap selection to the new plan array.
2. **Streaming actions span multiple components.** The toolbar initiates actions, App.tsx manages the IPC lifecycle, and LogPanel displays output. No single child component has enough context to own this flow.

<!-- Source: erkdesk/src/renderer/App.tsx, state declarations and child JSX -->

See the state declarations and JSX return in `App.tsx` for the full ownership picture.

## Auto-Refresh Selection Preservation

The 15-second auto-refresh re-fetches plan data from `erk exec dash-data`. The non-obvious problem: plans can reorder between fetches (e.g., a PR state change moves a plan up or down). If selection were tracked by array index, the user would suddenly be looking at a different plan after refresh.

**The solution**: Before applying new plan data, the refresh effect looks up the `issue_number` of the currently selected plan, then finds that issue_number's new index in the refreshed array. If the plan no longer exists, it falls back to index 0.

<!-- Source: erkdesk/src/renderer/App.tsx, setInterval effect -->

See the `setInterval` effect in `App.tsx` for the implementation. The key detail is that `setSelectedIndex` is called _inside_ the `setPlans` updater — this ensures the index remapping sees the new plan array, not the stale one.

## WebView Overlay Architecture

The right pane doesn't render GitHub content inside React. Instead, it uses a native Electron `WebContentsView` that overlays a placeholder `<div>`. This is a deliberate architectural choice with several consequences:

1. **SplitPane reports bounds, not content.** The right pane `<div>` is empty — SplitPane measures its bounding rect via `ResizeObserver` and sends it to the main process via `updateWebViewBounds` IPC. The main process positions the `WebContentsView` to match.

2. **URL loading goes through IPC, not React.** When selection changes, App.tsx sends the URL via `loadWebViewURL` IPC rather than setting a `src` prop. The `lastLoadedUrlRef` deduplicates this — without it, every re-render would trigger a redundant IPC call and page reload.

3. **pr_url takes priority over issue_url.** When both exist, App.tsx prefers the PR URL because PRs are more actionable (reviews, checks, merge status). This is a UX decision, not a technical constraint.

<!-- Source: erkdesk/src/renderer/App.tsx, URL loading effect -->
<!-- Source: erkdesk/src/renderer/components/SplitPane.tsx, reportBounds callback and ResizeObserver -->
<!-- Source: erkdesk/src/main/index.ts, webview:update-bounds handler -->

The three-way coordination between these files makes the overlay work: SplitPane reports geometry, App.tsx decides what URL to show, and main/index.ts positions the native view.

## Keyboard Navigation

App.tsx implements vim-style j/k navigation (plus arrow keys). The handler is a `useCallback` that depends on `plans.length` for bounds clamping. Two details worth knowing:

- The handler is registered as a global `keydown` listener on `document`, not on a specific element. This means keyboard nav works regardless of focus.
- Bounds clamping uses `Math.min`/`Math.max` to prevent negative indices or overflow. The early return on `plans.length === 0` prevents navigation when no data is loaded.

## Streaming Action Lifecycle

Action execution spans three components with a clear ownership boundary:

| Responsibility                               | Owner         |
| -------------------------------------------- | ------------- |
| Command generation and concurrency guard     | ActionToolbar |
| IPC streaming lifecycle and state management | App.tsx       |
| Output display and auto-scroll               | LogPanel      |

The critical insight: IPC event listeners (`onActionOutput`, `onActionCompleted`) are registered once on mount in a separate `useEffect`, not inside `handleActionStart`. This prevents listener accumulation — if listeners were registered per-action, each action would add another set without removing the old ones.

<!-- Source: erkdesk/src/renderer/App.tsx, handleActionStart callback and streaming useEffect -->

See `handleActionStart` and the streaming `useEffect` in `App.tsx`. The cleanup function calls `removeActionListeners()` which removes all listeners for both IPC channels.

## Related Documentation

- [Action Toolbar](action-toolbar.md) — Action definitions, availability predicates, and the data-driven pattern
- [IPC Actions](ipc-actions.md) — Four-location IPC checklist, streaming vs blocking patterns
- [erkdesk Tripwires](tripwires.md) — Critical patterns to follow
