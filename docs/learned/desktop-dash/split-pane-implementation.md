---
title: SplitPane Implementation
read_when:
  - working on split-pane layout, debugging bounds reporting, implementing resizable panels in erkdesk
---

# SplitPane Implementation

The `SplitPane` component provides a resizable two-panel layout where:

- **Left pane** contains React UI (file tree, controls, etc.)
- **Right pane** is a placeholder for Electron's `WebContentsView` overlay

## Component Architecture

**File**: `erkdesk/src/renderer/components/SplitPane.tsx`

### Props

```typescript
interface SplitPaneProps {
  leftPane: React.ReactNode; // Content for left panel
  minLeftWidth?: number; // Default: 200px
  minRightWidth?: number; // Default: 400px
  defaultLeftWidth?: number; // Default: 300px
}
```

### Constants

```typescript
const DIVIDER_WIDTH = 4; // Width of the draggable divider (in pixels)
```

**Note**: This constant is hardcoded in the component but critical for bounds calculations. It represents the space between the left pane and the WebContentsView.

## Bounds Reporting Lifecycle

The component reports WebContentsView bounds to the main process via `window.erkdesk.updateWebViewBounds()` on three triggers:

### 1. Initial Mount

When the component mounts, `reportBounds()` is called via `useEffect`:

```typescript
useEffect(() => {
  reportBounds();
}, [leftWidth, reportBounds]);
```

This ensures the WebContentsView is positioned correctly on initial render.

### 2. Divider Drag

When the user drags the divider to resize the split:

```typescript
const onMouseMove = (e: MouseEvent) => {
  const container = containerRef.current;
  if (!container) return;
  const containerRect = container.getBoundingClientRect();
  const maxLeft = containerRect.width - DIVIDER_WIDTH - minRightWidth;
  const newLeft = e.clientX - containerRect.left;
  setLeftWidth(Math.max(minLeftWidth, Math.min(maxLeft, newLeft)));
};
```

Setting `leftWidth` triggers the `useEffect` dependency, which calls `reportBounds()`.

### 3. Window Resize

When the window is resized, bounds must be recalculated:

```typescript
useEffect(() => {
  window.addEventListener("resize", reportBounds);
  return () => window.removeEventListener("resize", reportBounds);
}, [reportBounds]);
```

This ensures the WebContentsView stays correctly positioned when the window size changes.

## Bounds Calculation

The `reportBounds` function uses `getBoundingClientRect()` on the right pane placeholder:

```typescript
const reportBounds = useCallback(() => {
  const el = rightPaneRef.current;
  if (!el) return;
  const rect = el.getBoundingClientRect();
  window.erkdesk.updateWebViewBounds({
    x: rect.x,
    y: rect.y,
    width: rect.width,
    height: rect.height,
  });
}, []);
```

**Why this works**:

- The right pane div has `flex: 1`, so it expands to fill remaining space.
- `getBoundingClientRect()` returns the actual rendered position and size.
- The main process receives these measurements and applies them to the WebContentsView.

## Minimum Width Constraints

### Left Pane

```typescript
minLeftWidth = 200; // Default minimum
```

Enforced during drag:

```typescript
setLeftWidth(Math.max(minLeftWidth, Math.min(maxLeft, newLeft)));
```

### Right Pane

```typescript
minRightWidth = 400; // Default minimum
```

Enforced by calculating `maxLeft`:

```typescript
const maxLeft = containerRect.width - DIVIDER_WIDTH - minRightWidth;
```

This ensures the left pane cannot grow so large that the right pane would be smaller than `minRightWidth`.

## Defensive Bounds Handling

While the component reports measured bounds directly, the **main process** applies defensive clamping:

```typescript
// In erkdesk/src/main/index.ts
webView.setBounds({
  x: Math.max(0, Math.floor(bounds.x)),
  y: Math.max(0, Math.floor(bounds.y)),
  width: Math.max(0, Math.floor(bounds.width)),
  height: Math.max(0, Math.floor(bounds.height)),
});
```

**Rationale**: Even though React's `getBoundingClientRect()` should return valid values, the main process clamps to prevent:

- Negative coordinates (e.g., from browser quirks)
- Fractional pixels (Electron expects integer bounds)

See [Defensive Bounds Handling](defensive-bounds-handling.md) for details.

## Divider Interaction

### Dragging State

```typescript
const [isDragging, setIsDragging] = useState(false);
```

- `onMouseDown` on divider → `setIsDragging(true)`
- `onMouseUp` anywhere → `setIsDragging(false)`

### Visual Feedback

```typescript
backgroundColor: isDragging ? "#999" : "#ccc";
```

The divider darkens during drag to indicate active resizing.

### Cursor

```typescript
cursor: "col-resize";
```

Shows horizontal resize cursor when hovering over the divider.

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

The component does **not** handle cleanup — the main process removes IPC listeners when the window closes:

```typescript
// In erkdesk/src/main/index.ts
mainWindow.on("closed", () => {
  ipcMain.removeAllListeners("webview:update-bounds");
  ipcMain.removeAllListeners("webview:load-url");
  webView = null;
});
```

See [WebView API](webview-api.md) for IPC cleanup details.

## Related Documentation

- [WebView API](webview-api.md) — IPC channels and preload bridge
- [Defensive Bounds Handling](defensive-bounds-handling.md) — Why main process clamps bounds
