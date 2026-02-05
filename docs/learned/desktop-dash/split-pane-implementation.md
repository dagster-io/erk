---
title: SplitPane Implementation
read_when:
  - working on split-pane layout, debugging bounds reporting, implementing resizable panels in erkdesk
last_audited: "2026-02-05 09:48 PT"
audit_result: edited
---

# SplitPane Implementation

The `SplitPane` component provides a resizable two-panel layout where:

- **Left pane** contains React UI (file tree, controls, etc.)
- **Right pane** is a placeholder for Electron's `WebContentsView` overlay

**Source**: `erkdesk/src/renderer/components/SplitPane.tsx`

## Key Constants

- `DIVIDER_WIDTH = 4` — Width of the draggable divider in pixels, critical for bounds calculations

## Bounds Reporting Lifecycle

The component reports WebContentsView bounds to the main process via `window.erkdesk.updateWebViewBounds()` on four triggers:

1. **Initial mount** — `useEffect` with `[leftWidth, reportBounds]` dependency
2. **Divider drag** — Setting `leftWidth` state triggers the effect
3. **Window resize** — Event listener calls `reportBounds()`
4. **Right pane resize** — `ResizeObserver` detects size changes (e.g., when log panel appears)

**Why `getBoundingClientRect()` works**: The right pane div has `flex: 1`, so it expands to fill remaining space. The function returns the actual rendered position and size, which the main process applies to the WebContentsView.

## Minimum Width Constraints

- **Left pane**: `minLeftWidth` (default 200px) enforced via `Math.max()` during drag
- **Right pane**: `minRightWidth` (default 400px) enforced by calculating `maxLeft`:
  ```
  maxLeft = containerRect.width - DIVIDER_WIDTH - minRightWidth
  ```

This prevents the left pane from growing so large that the right pane would be smaller than `minRightWidth`.

## Defensive Bounds Handling

The **main process** applies defensive clamping (see `erkdesk/src/main/index.ts:47-52`):

- `Math.max(0, ...)` — Prevents negative coordinates from browser quirks
- `Math.floor(...)` — Electron expects integer bounds, not fractional pixels

See [Defensive Bounds Handling](defensive-bounds-handling.md) for details.

## Layout Structure

```
┌─────────────────────────────────────────────┐
│  Container (flex)                           │
│  ┌──────────┬──┬──────────────────────────┐│
│  │  Left    │  │  Right Pane (placeholder)││
│  │  Pane    │DI│  (WebContentsView        ││
│  │  (React) │VI│   overlays this)         ││
│  │          │DE│                           ││
│  │          │R │                           ││
│  └──────────┴──┴──────────────────────────┘│
│  ← leftWidth→←4→← flex: 1 (calculated)    →│
└─────────────────────────────────────────────┘
```

**Key points**:

- Left pane has fixed width (`leftWidth` state)
- Divider has fixed width (`DIVIDER_WIDTH = 4`)
- Right pane uses `flex: 1` to fill remaining space

## IPC Cleanup

The component does **not** handle cleanup — the main process removes all IPC listeners when the window closes. See `erkdesk/src/main/index.ts:190-201` for the cleanup code.

## Related Documentation

- [WebView API](webview-api.md) — IPC channels and preload bridge
- [Defensive Bounds Handling](defensive-bounds-handling.md) — Why main process clamps bounds
